# blender-plugin
I created a modified version of Marv's Blender Plugin for Re-Volt, that works in the current Blender (5.0)

INSTALLATION
place 'io_revolt' in Blender/"version"/scripts/addons/

-Theman with the help of AI and a bunch of friends in the RV I/O community.

20.26.13
Fixed .taz (Track Zones) export (addressed by sinaosal)

20.26.12
Fixed Visiboxes import / export
Fixed the naming of Visiboxes (in Blender)
Added Duplicate Visibox function
Cleaned the MakeItGood panel
Added Duplicate Track Zone function (requested by sinaosal)
Tex+VC+Alpha Material Preview has now more visible effect
.rim (Mirrors) import / export fix (addressed by Skitch)

20.26.11
Fixed HULL export
Improved handling of materials

20.25.99
Improved handling of materials

20.25.98
The Copy Params was fixed
Some icons in NCP Materials were removed
Added to exporting of car a function to correct orientation.
Fixed Freezing of Car Auto Shade

20.25.97
Export doesn't crash during exporting empty meshes

20.25.96
Improved Texture Handling
FUNCTION: Fix Texture N:o / Materials
FUNCTION: Load Textures from Disk
Removed unnecessary function from m_out

20.95.95
Fixed Creation of Texture Animations
Fixed a bug that occasionally crashed the (.m) export

20.25.94
Fixed Material Asssignment for various imports
Smoothened out the plugin in general (bmesh / edit mode)
Added Custom Face Properties for Models (.m files)
Changed first Texture Number back to 0

20.25.93
Fixed the rest of Blender 5.0 incompabilities

20.25.92
Fixed property issue in MaterialAssignment function

20.25.91
Added Batch Bake to Baking of Vertex Colours
Fixed Instance and Model UI
Fixed Batch Bake of Fin Env and Model Colour
Updated some old usages of 'imp' (old Python version)
Fixed some RNA links to use ID props

20.25.90
Updated the plugin to work in Blendrer 5.0

20.25.82
Fixed non-working RGB Model Colour
Fixed link in plugin the description

20.25.81
Bug fixes
Re-arranged the UI further
CAUTION: RBG Model Colour doesn't work

20.25.80
Improved Mixing of Texture and Vertec Colour
Re-arranged the UI (Check the Properties Window TABS)

20.25.79
Fixed UI - Texture Number

20.25.78
Minor fix to the Export window

20.25.77
Blender won't crash anymore when using (I)Inset
You can switch back to Texture from TEX+VC

20.25.76
.fob import now accepts -1 as a value
Changed the link to the manual

20.25.75
Fixed "Set Material to Selected Faces"
Fixed "Fix Texture Numbers and Materials" for texnum 26 (aa)
Fixed .fin (Instance) import / export function

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
