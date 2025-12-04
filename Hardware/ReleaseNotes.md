# Release Notes: Hardware

## Hardware 2.5.1

This is the first release of the project in [KiCAD](https://kicad.org).  The majority of the design is the same as 2.4.0, with small updates:
* Improved decoupling on some systems to provide a little less bounce on switching.
* Switched to a [TI](https://www.ti.com) part for the switch-mode power supply controller; slightly increased inductance in the feedback loop to better control loop oscillation and give better regulation on the output.
* Updated power monitoring system to allow us to measure the supply voltage (rather than just detecting whether it was connected or not).  This requires firmware 1.6.1 to be managed correctly (power monitoring should not be configured on for hardware 2.5.1 without firmware 1.6.1!)
* The layout of the power connector for external 12V power has been changed; check silkscreen for correct orientation.
* Four mounting holes have been added to the board to allow for it to be more securely mounted into an enclosure if required.  This slightly increases the size of the board.