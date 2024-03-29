#!/usr/bin/env python3
# coding: utf-8
"""@package synchronizer
Last modification 202007 by Kevin Krieger, with help from Dr. David Themens who tested on Windows
and provided required changes to sync a specific radar

This script is designed to log on to the University of Saskatchewan globus
SuperDARN mirror in order to check for and download new files for a specific pattern and data type

IMPORTANT: Before this script is run, there are a set of instructions which must be followed.
Please see this readme for details: https://github.com/SuperDARNCanada/globus/blob/master/README.md
***

The first time it is run, it will ask for a manual login
to globus, in order to get a refresh token. It will save the refresh token so that subsequent calls
to the script can be automated (example: via cron).

By default, this script will email you upon failure of the transfer, but not upon success.
To change this behaviour, you need to simply change the 'notify_on_succeeded=False,
notify_on_failed=True' values to True or False in the sync_files_from_list method.

By default, there is a soft timeout of 30 seconds per file for the transfer. If this amount of time
is exceeded, the script will return, but the transfer is likely still happening.
If you have a faster or slower connection, you may consider changing this value - it will not affect
the transfer, only the amount of time the script waits until returning.
To be sure about the status of your transfer, you can log into globus.org and view your transfers.

The script will check the arguments and if there are errors with the
arguments (for example, if the year is in the future, or the month is
not 1-12) then it will fail with an error message.
"""

from __future__ import print_function
import inspect
from datetime import datetime
from os.path import expanduser, isfile
import argparse
import globus_sdk
from globus_sdk.scopes import TransferScopes
import time
import sys
import platform

if sys.version_info >= (3, 0):
    PYTHON3 = True
else:
    PYTHON3 = False

USER_HOME_DIRECTORY = expanduser("~")
# The following is a path to a file that contains the globus transfer refresh tokens used
# for automatic authentication.
TRANSFER_RT_FILENAME = USER_HOME_DIRECTORY + "/.globus_transfer_rt"

# UUID of your endpoint, retrieve from endpoint info at: https://www.globus.org/app/endpoints
# Or from the filesystem that globusconnectpersonal is installed on.
# Note: this assumes you are running globusconnectpersonal & this script on the same filesystem

if platform.system() in 'Windows':
    PERSONAL_UUID_FILENAME = USER_HOME_DIRECTORY + "\AppData\Local\Globus Connect\client-id.txt"
else:
    PERSONAL_UUID_FILENAME = USER_HOME_DIRECTORY + "/.globusonline/lta/client-id.txt"

if isfile(PERSONAL_UUID_FILENAME):
    with open(PERSONAL_UUID_FILENAME) as f:
        PERSONAL_UUID = f.readline().strip()
else:
    raise FileNotFoundError("Client ID file not found: {}".format(PERSONAL_UUID_FILENAME))

# Client ID retrieved from https://auth.globus.org/v2/web/developers
# CLIENT_ID = '84d0b918-f49a-4136-a115-4206dafeba8a' Old from previous globus auth
CLIENT_ID = 'bc9d5b7a-6592-4156-bfb8-aeb0fc4fb07e'


class Synchronizer(object):
    """ This is the synchronizer class. It knows about globus and will
    synchronize a given local directory with the globus SuperDARN mirror given by it's UUID
    Note:documentation at http://globus-sdk-python.readthedocs.io/en/stable/ was used extensively"""

    def __init__(self, client_id, client_secret=None, transfer_rt=None):
        """ Initialize the Synchronizer class by getting dates/times, arguments, checking for errors
        and finally getting a transfer client and mirror UUID to use.

            :param client_id: Retrieved from https://auth.globus.oorg/v2/web/developers for you
            :param client_secret: Not normally used, but another way of authentication
            :param transfer_rt: Transfer refresh token, used for automating authentication
        """
        self.cur_year = datetime.now().year
        self.cur_month = datetime.now().month
        self.possible_data_types = ['raw', 'dat', 'fit', 'fitacf_25', 'fitacf_30', 'despeck_fitacf_30']

        # CLIENT_ID and CLIENT_SECRET are retrieved from the "Manage Apps" section of
        # https://auth.globus.org/v2/web/developers for this app. transfer_rt is retrieved
        # by looking for it at the path given by global variable TRANSFER_RT_FILENAME.
        self.CLIENT_ID = client_id
        self.CLIENT_SECRET = client_secret
        self.TRANSFER_RT = transfer_rt
        self.transfer_rt_filename = TRANSFER_RT_FILENAME

        parser = argparse.ArgumentParser(description="This script will sync a specified year, month"
                                                     "and data type to your specified local dir."
                                                     "** Note that you may require quotation marks"
                                                     "around the pattern. **",
                                         usage=""" Examples
sync_radar_data_globus.py /home/username/current_month_rawacfs/
sync_radar_data_globus.py -y 2016 -m 05 /home/username/201605_rawacfs/
sync_radar_data_globus.py -y 2004 -m 02 -t dat /home/username/200402_dat_files/
sync_radar_data_globus.py -y 2014 -m 12 -p 20141201*sas /home/username/20141201_sas_rawacfs/
sync_radar_data_globus.py -p rkn /home/username/cur_month_rkn_rawacfs/
sync_radar_data_globus.py -y 2004 -m 02 -t dat -p 20040212 /home/username/20040212_dat_files/
sync_radar_data_globus.py -y 2020 -m 01 -t fitacf_25 -p 20200101*inv /home/username/inv_fitacf/
sync_radar_data_globus.py -y 1993 -m 12 -t fit -p 19931201 /home/username/1993_dec_1_fit/

** NOTE that you must have appropriate permissions to access the FITACF 2.5 files **""",
                                         formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument("-y", "--sync_year", type=int, default=self.cur_year,
                            help="Year you wish to sync data for. Default is current year")
        parser.add_argument("-s", "--sync_station", type=str, default="*",
                            help="Which radar to download data for, default all radars")
        parser.add_argument("-m", "--sync_month", type=int, default=self.cur_month,
                            help="Month you wish to sync data for. Default is current month")
        parser.add_argument("-p", "--sync_pattern", default='*',
                            help="""Sync pattern. default: '*'
Examples:
1)'-p=20180101' Download January 1st 2018 files (requires inputting -y and -m as 2018 and 01)
2)'-p=ade' Download ade files for specified year and month
3)'-p=2010503*kod.c' Download all kod.c files from 20160503""")
        parser.add_argument("-t", "--data_type", choices=self.possible_data_types, default='raw')
        parser.add_argument("sync_local_dir", help="Path on endpoint to sync data to")
        args = parser.parse_args()

        self.radar_code = args.sync_station
        self.sync_year = args.sync_year
        self.sync_month = "{:02d}".format(args.sync_month)
        self.sync_pattern = args.sync_pattern
        self.data_type = args.data_type
        self.sync_local_dir = args.sync_local_dir
        # **Note** for some globus instances a tilde is required in front of the forward slash
        # for the mirror_root_dir, example: "~/chroot/sddata"
        if self.data_type in ["raw", "dat", "fit"]:
            self.mirror_root_dir = "/chroot/sddata"
        else:
            self.mirror_root_dir = "~/local_data"
        self.sanity_check()

        # Potential consents required (new as of Globus enpoints v5 - see here: https://globus-sdk-python.readthedocs.io/en/stable/examples/minimal_transfer_script/index.html#example-minimal-transfer)
        self.consents = []

        # Get a transfer client
        self.transfer_client = self.get_transfer_client()
        self.mirror_uuid = self.get_superdarn_mirror_uuid()

    def sanity_check(self):
        """ Check arguments: year, month, data type. Kills script if something is
        wrong. """
        if int(self.sync_year) == self.cur_year and int(self.sync_month) > self.cur_month:
            raise ValueError("Sync month \"{}\" is in the future.".format(self.sync_month))
        if int(self.sync_year) > self.cur_year:
            raise ValueError("Sync year \"{}\" is in the future.".format(self.sync_year))
        if int(self.sync_month) < 1 or int(self.sync_month) > 12:
            raise ValueError("Sync month \"{}\" invalid.".format(self.sync_month))
        # Note we cannot check the path here with typical os.is_path
        # since we may be running this script on a different machine than the destination endpoint,
        # therefore the script will fail with exception from globus if it doesn't exist.
        # Note that this means that the PERSONAL_UUID retrieval would have to change from default
        # since it is currently retrieved from the filesystem (assumes this is running on the same
        # filesystem that globusconnectpersonal is installed on)

    def synchronize(self):
        """ Do synchronization of files from the globus SuperDARN mirror to the user's endpoint """
        # Step 1 - Download files listing from server.
        # Go through listing, remove lines that don't correspond to requested pattern
        try:
            # You absolutely need the '~' in front of the root of the path for the patterns to work.
            # This isn't obvious from documentation.
            listing_path = "{root}/{type}/{year}/{month}/".format(root=self.mirror_root_dir,
                                                                  type=self.data_type,
                                                                  year=self.sync_year,
                                                                  month=self.sync_month)
            # The listing pattern is handled by the python globus sdk
            listing_pattern = "name:~*{}*".format(self.sync_pattern)
            if 'raw' in self.data_type:
                listing_pattern = "name:~*{}*rawacf.bz2".format(self.sync_pattern)
            elif 'dat' in self.data_type:
                listing_pattern = "name:~*{}*dat.bz2".format(self.sync_pattern)
            elif 'fitacf_25' in self.data_type:
                listing_pattern = "name:~*{}*.fitacf.bz2".format(self.sync_pattern)
            elif 'fitacf_30' in self.data_type:
                listing_pattern = "name:~*{}*.fitacf.bz2".format(self.sync_pattern)
            elif 'despeck_fitacf_30' in self.data_type:
                listing_pattern = "name:~*{}*.despeck.fitacf.bz2".format(self.sync_pattern)
            elif 'fit' in self.data_type:
                listing_pattern = "name:~*{}*.fit.gz".format(self.sync_pattern)
            else:
                pass
            print("Listing path: {path} on endpoint: {endpoint} with pattern: {pattern}".format(
                path=listing_path, endpoint=self.mirror_uuid, pattern=listing_pattern))
            print("Note: This can take several minutes")
            listing_succeeded = False

            # The number of retries required to reliably succeed, on cedar's endpoint, to get
            # around the timeout issue.
            operation_ls_retries = 15
            attempts = 0
            listing = []
            listing_times = []

            while attempts < operation_ls_retries:
                try:
                    listing_times.append(time.time())
                    if PYTHON3:
                        print(".", end="", flush=True)
                    else:
                        print("."),
                        sys.stdout.flush()

                    listing = self.transfer_client.operation_ls(self.mirror_uuid, path=listing_path,
                                                                filter=listing_pattern)
                    listing_succeeded = True
                    break
                except globus_sdk.GlobusAPIError:
                    listing_succeeded = False
                    attempts += 1
                except globus_sdk.GlobusTimeoutError:
                    listing_succeeded = False
                    attempts += 1

            print("")
            if not listing_succeeded:
                sys.exit("Listing failed after {} attempts! Exiting".format(attempts))

            files_to_sync = [entry['name'] for entry in listing]
            # Max duration of transfer is set to 30 seconds per file here to give plenty of time.
            # A more proper way to do this would be to get the sizes of the files to transfer
            # and calculate approximate time from that, given a typical network speed. This works
            # fine 99% of the time though.
            task_max_duration_s = len(files_to_sync) * 30
            print("Transferring {} files with a soft timeout of {} s.".format(len(files_to_sync),
                                                                              task_max_duration_s))

            # Step 2 - Use the file listing from step 1 and globus sync level 3 (checksum) to sync
            # requested pattern files. Block on this but timeout after a certain amount of time.
            transfer_result = self.sync_files_from_list(files_to_sync)
            completed = self.transfer_client.task_wait(transfer_result["task_id"],
                                                       timeout=task_max_duration_s,
                                                       polling_interval=30)
            if not completed:
                print("Transfer didn't complete yet but may still be running. Please check "
                      "https://app.globus.org/activity if you want to check status of transfer")
            else:
                print("Transfer finished")

        except globus_sdk.GlobusAPIError as e:
            print("Globus API error\nError code: {}\nError message: {}".format(e.code, e.message))
        except globus_sdk.GlobusConnectionError:
            print("Globus Connection Error - error communicating with REST API server")
        except globus_sdk.GlobusTimeoutError:
            print("Globus Timeout error - REST request timed out.")
        except globus_sdk.NetworkError:
            print("Network error")

    def get_first_globus_connect_personal_uuid(self):
        """ Will search user's endpoints and retrieve the UUID of the first active globus connect
        personal endpoint.

        :returns: UUID of first active globus connect personal endpoint """

        gcp_eps = self.transfer_client.endpoint_search(filter_scope='my-gcp-endpoints')
        if gcp_eps is not None:
            for ep in gcp_eps:
                if ep['activated'] is True and ep['gcp_connected'] is True:
                    return ep['id']
            sys.exit("No endpoint found for Globus Connect Personal endpoint. Exiting")

    def get_superdarn_mirror_uuid(self):
        """ Will search endpoints and retrieve the UUID of the SuperDARN mirror endpoint.

        :returns: UUID of SuperDARN mirror endpoint """

        for ep in self.transfer_client.endpoint_search('SuperDARN mirror'):
            if 'carley.martin@usask.ca' in ep['contact_email'] and 'updated SuperDARN Mirror using Globus v5' in ep['description']:
                return ep['id']
        sys.exit("No endpoint found for SuperDARN mirror. Exiting")

    def get_refresh_token_authorizer(self):
        """ Attempts to get an authorizer object that uses refresh tokens (for
        automatic authentication). It requires a refresh token to work.

        :returns: Globus SDK authorizer object """

        # Get client from globus sdk to act on
        client = globus_sdk.NativeAppAuthClient(self.CLIENT_ID)
        client.oauth2_start_flow(refresh_tokens=True)

        # Get authorizer that handles the refreshing of token
        try:
            return globus_sdk.RefreshTokenAuthorizer(self.TRANSFER_RT, client)
        except globus_sdk.exc.AuthAPIError as e:
            sys.exit("Transfer refresh token file {} is outdated, "
                     "please remove and try running again".format(self.transfer_rt_filename))

    def get_client_secret_authorizer(self):
        """ Attempts to get an authorizer object that uses a client secret for authentication.
        Not normally used.

        :returns: Globus SDK authorizer object """
        client = globus_sdk.ConfidentialAppAuthClient(self.CLIENT_ID, self.CLIENT_SECRET)
        token_response = client.oauth2_client_credentials_tokens()

        # the useful values that you want at the end of this
        globus_transfer_data = token_response.by_resource_server['transfer.api.globus.org']
        globus_transfer_token = globus_transfer_data['access_token']

        return globus_sdk.AccessTokenAuthorizer(globus_transfer_token)

    def get_auth_with_login(self, consents=TransferScopes.all):
        """ Attempts to get an authorizer object that requires manual authentication,
        but will return a refresh token and save it to  a local file for future use.

        :param: consents: globus sdk version 5 endpoints require consent scopes, this is the list
                          of those that we will request, to access the endpoints and paths we need
        :returns: Globus SDK authorizer object """

        client = globus_sdk.NativeAppAuthClient(self.CLIENT_ID)
        client.oauth2_start_flow(refresh_tokens=True, requested_scopes=consents)

        authorize_url = client.oauth2_get_authorize_url()
        print('Please go to this URL and login: {0}'.format(authorize_url))

        # Handle both python 3 and python 2
        if PYTHON3:
            auth_code = input('Please enter the code you get after login here: ').strip()
        else:
            auth_code = raw_input('Please enter the code you get after login here: ').strip()
        token_response = client.oauth2_exchange_code_for_tokens(auth_code)

        globus_transfer_data = token_response.by_resource_server['transfer.api.globus.org']
        globus_transfer_token = globus_transfer_data['access_token']
        # Native apps - transfer_rt are refresh tokens and are lifetime credentials,
        # so they should be kept secret
        # The consents for these credentials can be seen at https://auth.globus.org/v2/web/consents
        print("Here is your refresh token: {}. It has been written to the file {}".
              format(globus_transfer_data['refresh_token'], self.transfer_rt_filename))
        with open(self.transfer_rt_filename, 'w') as transfer_rt_file:
            transfer_rt_file.write(globus_transfer_data['refresh_token'])

        print("Note: refresh tokens are lifetime credentials, they should be kept secret. Consents "
              "for these credentials are managed at https://auth.globus.org/v2/web/consents")

        return globus_sdk.AccessTokenAuthorizer(globus_transfer_token)

    def get_transfer_client(self):
        """ Determines what type of authorizer to get in order to initialize the TransferClient
        object which is used for many Globus SDK tasks (such as transferring files). Depending upon
        whether or not the user has a refresh token or a client secret, the refresh token
        authorizer, client secret authorizer or manual authorizer will be used.

        :returns: Globus SDK Transfer Client object """

        if self.TRANSFER_RT is not None:
            return globus_sdk.TransferClient(authorizer=self.get_refresh_token_authorizer())
        elif self.CLIENT_SECRET is not None:
            return globus_sdk.TransferClient(authorizer=self.get_client_secret_authorizer())
        else:
            return globus_sdk.TransferClient(authorizer=self.get_auth_with_login())

    def check_for_consent_required(self, ep_uuid=None, path=None):
        """Call this function with all endpoint uuids that you're going to use (source and destination)
        along with all paths to be used, so that we get all the required consents at the beginning.
        New and required as of Globus endpoints v5. This modifies the self.consents list by extending it
        Defaults to the mirror endpoint and root directory, but can and should also be called on the
        other endpoint(s) you want to transfer to/from.

        :param: ep_uuid: UUID of the endpoint you want to find required consent scopes for
        :param: path: the path on the endpoint you want to find the required consent scopes for """
        if ep_uuid is None:
            ep_uuid = self.mirror_uuid
        if path is None:
            path = self.mirror_root_dir
        try:
            self.transfer_client.operation_ls(ep_uuid, path=path)
        # If there's an exception due to lack of consents, then add the consent scopes required
        # to our list, so we can use them all a second time to login
        except globus_sdk.TransferAPIError as err:
            if err.info.consent_required:
                self.consents.extend(err.info.consent_required.required_scopes)

    def sync_files_from_list(self, files_list, source_uuid=None, dest_uuid=None):
        """ Takes a list of files to synchronize as well as source and destination endpoint UUIDs.
        It is hard coded to place the files in the correct YYYY/MM directories on the SuperDARN
        globus mirror, the default source and destination UUIDs are fine for 99% of usage.

        :param files_list: python list of file names to synchronize
        :param source_uuid: UUID of the source endpoint of the files
        :param dest_uuid: UUID of the destination endpoint for the files
        :returns: Globus SDK transfer result object """

        if dest_uuid is None:
            dest_uuid = PERSONAL_UUID
        if source_uuid is None:
            source_uuid = self.mirror_uuid
        function_name = inspect.currentframe().f_code.co_name
        transfer_data = globus_sdk.TransferData(self.transfer_client, source_uuid, dest_uuid,
                                                label=function_name, sync_level="checksum",
                                                notify_on_succeeded=False,
                                                notify_on_failed=True)

        source_dir_prefix = "{root}/{type}/{year}/{month}/".format(root=self.mirror_root_dir,
                                                                   type=self.data_type,
                                                                   year=self.sync_year,
                                                                   month=self.sync_month)
        dest_dir_prefix = self.sync_local_dir
        for data_file in files_list:
            transfer_data.add_item("{source_dir}/{file_name}".format(source_dir=source_dir_prefix,
                                                                     file_name=data_file),
                                   "{dest_dir}/{file_name}".format(dest_dir=dest_dir_prefix,
                                                                   file_name=data_file))
        transfer_result = self.transfer_client.submit_transfer(transfer_data)
        return transfer_result


if __name__ == '__main__':
    """ Open the transfer refresh token file if it exists and use it to initialize a Synchronizer
    object. Then synchronize! """
    if isfile(TRANSFER_RT_FILENAME):
        with open(TRANSFER_RT_FILENAME) as f:
            sync = Synchronizer(CLIENT_ID, transfer_rt=f.readline())
    else:
        sync = Synchronizer(CLIENT_ID)
        # Now check for all consents required on the globus endpoint and personal endpoint
        sync.check_for_consent_required()
        sync.check_for_consent_required(PERSONAL_UUID, sync.sync_local_dir)
        if sync.consents:
            print("One of the endpoints being used requireds extra consent in order to be used, and you must login "
                  "a second time (dumb I know) to get those consents.")
        sync.get_auth_with_login(sync.consents)

    sync.synchronize()
