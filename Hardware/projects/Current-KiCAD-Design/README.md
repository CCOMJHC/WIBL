# KiCAD Hardware Design Files

## Introduction

This directory contains all of the files required for the [KiCAD](https://www.kicad.org) projects associated with the [WIBL](https://wibl.ccom.unh.edu) project.  You will need at least v. 9.0 of KiCAD to use the files.

## Portability

There have been some reported issues with project files containing hard-coded directory and filenames, which makes them a little less portable than would be preferred.  If this happens, you can point at the new location of schematic symbols and footprint libraries by:

1. Open [the project file](WIBL.kicad_pro) in KiCAD.
2. Open menu Peferences > Manage Symbol Libraries
    - Switch to the "Project Specific Libraries" tab.
    - Click on the cell containing the pathname for the "WIBL-eagle-import" library, and navigate to the [WIBL-eagle-import.kicad_sym](WIBL-eagle-import.kicad_sym) file.
    - Click "OK" to save.
3. Open menu Preferences > Manage Footprint Libraries
    - Switch to the "Project Specific Libraries" tab.
    - Click on the cell containing the pathname for the "WIBL" library, and navigate to the [WIBL.pretty](WIBL.pretty/) directory.
    - Click "OK" to save.

After this, you can check that the project is working appropriately by using the Electrical Rules Check (ERC) in schematic editor, and Design Rules Check (DRC) in PCB editor.  There may be one or two warnings, but there shouldn't be a tonne of warnings about missing libraries or symbols.
