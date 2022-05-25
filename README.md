# Setup the Arista EOS container

## Instructions
1. Download cEOS from the arista site(free registration required).
2. Run cEOS.sh passing in the path to cEOS file and cEOS version(used to tag image).

### Example
```sh
# assuming cEOS file named cEOS64-lab-4.28.0F.tar.xz in same directory
./cEOS.sh cEOS64-lab-4.28.0F.tar.xz 4.28.0F
```

### Notes
The Pci.py file is already built in the container. But the commented out assert statement on line 26 causes startup to fail for me. I have not bothered to look into why, It could just be a config error on my part.
