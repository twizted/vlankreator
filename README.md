VLANKreator
===========

# Description
A utility I wrote to test network equipment setup, specifically VLAN trunking 
and tagging. It is intended to be used on two machines connected to the network
equipment with configured VLANs, and they should be able to use the VLANs for
communication. Once it initializes the VLAN interfaces it can peform a ping 
sweep over them all to see if the other side is reachable. When exiting it 
destroys the created VLAN interfaces.

# Usage
Run the script without parameters to see usage.

# Requirements
No additional requirements.

