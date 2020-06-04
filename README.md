# globus

To get globus set up on your machine and access to the SuperDARN mirror:
1. go to globus.org (login button in top right -> then on the next page "use
Globus ID to sign up" near middle to bottom of page)
1. On the next page, it will have a link saying "Need a Globus ID? Sign Up". Click that link.
1. Create a Globus ID (username, password, name, email, organization,
etc...)
1. Log in to globus via login button on globus.org
1. Click on "Endpoints" tab
1. Click on "add Globus Connect Personal endpoint"
1. Now follow steps 1 and 2 on the page ("Get your globus connect personal setup 
key" and "Download & Install Globus Connect Personal")
1. Contact us with your globus username to share the SuperDARN endpoint with you

Now to get these scripts working you need to do the following:

1. Use python 3
1. Install pip if you don't have it: on OpenSuSe: sudo zypper in python-pip
1. Install the globus sdk for python: sudo pip3 install globus-sdk OR sudo pip install globus-sdk
1. Now make sure the script is runnable: chmod +x sync_radar_data_globus.py
1. Now run the script with some arguments, such as:

```
./sync_radar_data_globus.py -y 2007 -m 01 -p 20070101*sas /path/to/endpoint/dir
```

it will ask you to log into globus to authenticate, give you a token to paste into the cmd line,
then it will save a refresh token to a file on your computer to use for automatic login from now on.

