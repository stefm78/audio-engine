import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from audio_engine.sound import acquisition


def commons_page(pageid, title, *, license_name, license_url, description="bell cathedral", sample_url=None):
    return {
        "pageid": pageid,
        "title": title,
        "imageinfo": [{
            "url": sample_url or f"https://upload.wikimedia.org/{pageid}.ogg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_"),
            "mime": "audio/ogg",
            "mediatype": "AUDIO",
            "size": 1000,
            "extmetadata": {
                "LicenseShortName": {"value": license_name},
                "LicenseUrl": {"value": license_url},
                "Artist": {"value": "Example"},
                "ImageDescription": {"value": description},
            },
        }],
    }


class EligibleSoundDiscoveryTests(unittest.TestCase):
    def test_wikimedia_skips_ineligible_licenses_before_filling_limit(self):
        payload = {
            "query": {
                "pages": [
                    commons_page(
                        1,
                        "File:Share alike cathedral bell.ogg",
                        license_name="CC BY-SA 4.0",
                        license_url="https://creativecommons.org/licenses/by-sa/4.0/",
                    ),
                    commons_page(
                        2,
                        "File:CC0 cathedral bell.ogg",
                        license_name="CC0",
                        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                    ),
                ]
            }
        }
        with patch.object(acquisition, "_http_json", return_value=payload):
            results = acquisition.discover_wikimedia("cathedral bell", limit=1, required_tags=["bell"])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "commons-2")
        self.assertEqual(results[0]["license_id"], "CC0-1.0")

    def test_wikimedia_required_tags_are_prefiltered_before_download(self):
        payload = {
            "query": {
                "pages": [
                    commons_page(
                        3,
                        "File:Cathedral speech.ogg",
                        license_name="CC0",
                        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                        description="spoken cathedral tour",
                    ),
                    commons_page(
                        4,
                        "File:Church bell.ogg",
                        license_name="CC BY 4.0",
                        license_url="https://creativecommons.org/licenses/by/4.0/",
                        description="church bell ringing",
                    ),
                ]
            }
        }
        with patch.object(acquisition, "_http_json", return_value=payload):
            results = acquisition.discover_wikimedia("cathedral", limit=8, required_tags=["bell"])
        self.assertEqual([item["id"] for item in results], ["commons-4"])

    def test_openverse_filters_to_autonomous_license_then_reverifies_commons(self):
        calls = []
        landing = "https://commons.wikimedia.org/wiki/File:Eligible_bell.ogg"
        openverse_payload = {
            "results": [{"id": "ov-1", "foreign_landing_url": landing}]
        }
        commons_payload = {
            "query": {
                "pages": [commons_page(
                    5,
                    "File:Eligible bell.ogg",
                    license_name="CC0",
                    license_url="https://creativecommons.org/publicdomain/zero/1.0/",
                    description="distant church bell",
                )]
            }
        }

        def fake_http(url, timeout=20):
            calls.append(url)
            if "api.openverse.org" in url:
                return openverse_payload
            return commons_payload

        with patch.object(acquisition, "_http_json", side_effect=fake_http):
            results = acquisition.discover_openverse("church bell", limit=1, required_tags=["bell"])

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["license_id"], "CC0-1.0")
        self.assertTrue(results[0]["source_metadata_verified"])
        openverse_call = next(url for url in calls if "api.openverse.org" in url)
        query = parse_qs(urlparse(openverse_call).query)
        self.assertEqual(query["license"], ["cc0"])


if __name__ == "__main__":
    unittest.main()
