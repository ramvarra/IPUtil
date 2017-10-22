# IPUtil
### Author: Ram Varra 

##Lookup an IP Address in a list of IP subnet ranges using AVL Trees.

In a large network environement there can be many thousands of subnets with different sizes.  Subnet databases will normally consist of `subnet range (CIDR notation)` and other attributes such as `location`, `environment(dev or prod)`, etc.

Network analytic  solutions require finding match of a given IP Addresses to its subnet.  Tradition method for accomplishing this with a list of subnet ranges and linear search to find range match will not be optimal for response time.  

AVLTree will enable optimal search performance of the large ranges of the subnets for individual IP Address lookup.  The implementation benchmark with 1280 IP addresses in a ~26000 subnets yields followng results.
###### Linear Search:  65 seconds
###### AVL Search:  0.3 seconds (216 times faster!!!)

This utility implements the IPRange lookup using AVLTree. The solution depends on a subnet database (CSV) file with an attribute called `Range` that should contain the subnet range in CIDR format.  All other attributes are returned back as part of the lookup results.

The algorithm handles overlapping ranges by matching narrower subnet first.

The solution uses `Tim Rijavec` (tim@coder.si http://coder.si) implementation of AVLTree and extends it to handle range searches.


