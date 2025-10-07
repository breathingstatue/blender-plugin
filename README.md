# blender-plugin
I created a modified version of Marv's Blender Plugin for Re-Volt, that works in the current Blender (4.3)

INSTALLATION
place 'io_revolt' in Blender/"version"/scripts/addons/

-Theman with the help of AI and a bunch of friends in the RV I/O community.

20.25.70
Added Texture+Vertex Colour Layer Preview
TEX+VC Preview adjusts to the Vertex Alpha level

20.25.60
Fixed a bug in .fin (Instance) Import

20.25.55
Fixed a bug in export functions
Fixed a bug in .hul import
Added Visiboxes (.vis) import / export / creation
Removed ta_csv (.csv files for texture animations)
Added / Modified some elements in the UI
Finalized tri_out and taz_out (the beginning of the file was missing out 4-8bytes)

20.25.50
Objects import / export / duplicate (.fob)
Car Auto Shader
fixed some functions (e.g. 'Rename Textures' and 'Save Textures to Disk')
improved UI
fixed CarShadow generator
improved handling of textures / texture pages
broader .m (Model) Support

FULL CHANGELOG:

20.25.35
added NCP Material Preview 
car parts can have any default texture, not just car.bmp 
fixed a bug with multiple ViewLayers in Blender 

20.25.2
improved car import / parameters export
especially the handling of length parameter

20.25.1
fixed .hul import / export
fixed Convex Hull Tool

20.24.11
fixed bugs for Vertex Colouring
fixed bugs for NCP materials

20.24.10
Streamlined Car import / parameters Export
.m files Material Assignment
bug fixes to Material Assignment
bug fixes and improvements to Import & Export modules

20.24.9
Bugfixes for Car import and Material Preview
UI improvement
Improved Car Shadow Baking
Improved Car Texture Selector
camber import / export for Cars

20.24.8
Texture Number Assigner
Texture Animations editor
Car Skin Selector
Car Import (import all skins list via parameteres.txt)
Improved Car Shadow baking
Texture animations for .m file
Improved import/export modules
Added some face properties (face_texture_animation, face_ncp_no_planar)
Deleted some duplicate code (Vertex Light Baking had some duplicate code)
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
Deleted props modules and removed custom property "revolt"
Changes from the start: new panels and buttons, structural changes, operator labeling, registrations