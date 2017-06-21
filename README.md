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
1) Go to https://auth.globus.org/v2/web/developers
    a) Add a project named 'SuperDARN' or something similar
    b) Add an app to that project called 'sync_radar_data'
    c) Add three scopes to the app:
i) urn:globus:auth:scope:transfer.api.globus.org:all (Transfer files using Globus Transfer)
ii) openid (Know who you are in Globus.)
iii) email (Know your email address.)
    d) The redirect url is : https://auth.globus.org/v2/web/auth-code
    e) Click the "Native App" checkbox
    f) Click 'create app'
    g) Now you have a 'client ID' available to you, used in the script sort of as your user name.

2) Install pip if you don't have it: on OpenSuSe: sudo zypper in python-pip
2.1) Install the globus sdk for python: sudo pip2 install globus-sdk OR sudo pip install globus-sdk
3) Edit the script to include your client_id on line 'CLIENT_ID ='
and the uuid of your endpoint on line 'PERSONAL_UUID ='
(found at "Endpoints" link of globus.org when you're logged in,
click on the endpoint then you'll see uuid in the information that pops up)
4) Now make sure the script is runnable: chmod +x sync_radar_data_globus.py
5) Now run the script with some arguments, such as:
"./sync_radar_data_globus.py -y 2007 -m 01 -p 20070101*sas /path/to/endpoint/dir"
it will ask you to log into globus to authenticate, give you a token to paste into the cmd line,
then it will save a refresh token to a file on your computer to use for automatic login from now on.

