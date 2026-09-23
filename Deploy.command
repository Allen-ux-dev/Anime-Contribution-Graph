#!/bin/bash
cd "$(dirname "$0")"
clear
bash "./deploy.sh"
echo
read -n 1 -s -r -p "Press any key to close..."
echo
