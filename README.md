# blender-plugin
I created a modified version of Marv's Blender Plugin for Re-Volt, that works in the current Blender (4.1)

INSTALLATION
place io_revolt in Blender/"version"/scripts/addons/

-Theman with the help of Chat GPT

TO DO LIST:

20.24.?
Objects (.fob)
Texture Animations Editor

FULL CHANGELOG:

20.24.8
.m (Model) import/export
Pins import/export
Spinner import/export
Triggers import / export (value now Limited to 1024)
Track Zones import / export (reversable Zone IDs)
Texture Animations import/export (added set Max Slots)
Light Baking to Col / Fin Env / RGB
Vertex Color / Alpha / Env / EnvAlpha Layers (fixed bugs)
Material Change (added Set to All / Set to Selected)
Fixed import/export bugs

20.24.7
Copy Car Parameters to Clipboard fine-tuning to default values
Export to top menu
Some tool tips
Fixed WorldCut bugs
spring.prm and axle.prm import/export

20.24.6
Added WorldCut
Import to top menu

20.24.4
First release

20.24.3
I don't include props modules or custom attribute revolts, I'll see if bpy.context.scene works in import/export.

Changes: new panels and buttons, structural changes, operator labeling, registrations