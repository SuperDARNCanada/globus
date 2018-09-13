# globus

To get globus set up on your machine and access to the SuperDARN mirror:
1) go to globus.org (login button in top right -> then on the next page "use
Globus ID to sign up" on bottom of page)
2) Create a Globus ID (username, password, name, email, organization,
etc...)
3) Log in to globus via login button on globus.org
4) Click on "Endpoints" tab
5) Click on "add Globus Connect Personal endpoint"
6) Now follow steps 1 and 2 on the page ("Get your globus connect personal
setup key" and "Download & Install Globus Connect Personal")
7) Contact us with your globus username to share the SuperDARN endpoint with you



Now to get these scripts working you need to do the following:
1) Use python 3
2) Install pip if you don't have it: on OpenSuSe: sudo zypper in python-pip
2.1) Install the globus sdk for python: sudo pip2 install globus-sdk OR sudo pip install globus-sdk
3) Now make sure the script is runnable: chmod +x sync_radar_data_globus.py
4) Now run the script with some arguments, such as:
"./sync_radar_data_globus.py -y 2007 -m 01 -p 20070101*sas /path/to/endpoint/dir"
it will ask you to log into globus to authenticate, give you a token to paste into the cmd line,
then it will save a refresh token to a file on your computer to use for automatic login from now on.

