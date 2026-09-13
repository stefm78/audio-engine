# French native narration default — decision record

Status: implementation candidate

Human evidence from the Séville French-lock A/B probe validated the native French `fr-FR-HenriNeural` candidate over the current multilingual narrator for continuous French narration. The observed defect class is spontaneous language switching in otherwise French narration when multilingual provider voices encounter foreign proper names.

Bounded policy:

- ordinary French narration uses the standard `narrateur-vif` preset;
- `narrateur-vif` is locked to the native French `fr-FR-HenriNeural` provider voice;
- explicit provider voices remain explicit and are never silently recast;
- other role-specific presets remain unchanged; changing them requires their own casting evidence;
- foreign proper names are not rewritten or artificially francised;
- automatic tests prove configuration and resolution only; perceptual quality remains governed by human listening evidence.

This solves the generic default-narration path without pretending that every multilingual role preset has been independently qualified for replacement.
