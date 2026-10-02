# Notes for `backend/src/sro/application/integrations/listing.py`

Comments and docstrings moved out of [`backend/src/sro/application/integrations/listing.py`](../../../../../../../backend/src/sro/application/integrations/listing.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## `ListIntegrations.execute`, [line 56](../../../../../../../backend/src/sro/application/integrations/listing.py#L56): Comment

Code: `name in made,`

> `connected` is Nango holding a healthy connection for this operator and `linked` is the
> connector also holding a bearer it accepts. Folded into one flag, a failed link (key unset or
> rotated, the tab closed before the connect event) read as "not connected" and Connect made a
> second Nango connection for the same end user. Apart, the console offers Finish linking.
