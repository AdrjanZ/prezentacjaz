import requests
import json
import pydnsbl
import pandas as pd
from licensing.models import *
from licensing.methods import Key, Helpers
import os
import threading
import csv
from time import sleep

RSAPubKey = ""
auth = ""

if os.path.exists("Checked.csv") is False:
    with open("Checked.csv", mode="w", newline="", encoding="utf-8") as f:
        csv_writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(
            ["Proxy", "Fraud score", "Blacklisted", "CountryCode", "Region", "City", "Ip", "ISP",
             "Bot status", "If Proxy", "VPN", "Tor", "Recent Abuse"])


done_threads = []


class ProxyChecker:
    def __init__(self):
        pass

    @staticmethod
    def validate_license(key_):
        key = key_
        result = Key.activate(token=auth, \
                              rsa_pub_key=RSAPubKey, \
                              product_id=, \
                              key=key, \
                              machine_code=Helpers.GetMachineCode())

        if result[0] == None or not Helpers.IsOnRightMachine(result[0]):
            # an error occurred or the key is invalid or it cannot be activated
            # (eg. the limit of activated devices was achieved)
            print("The license does not work: {0}".format(result[1]))
        else:
            # everything went fine if we are here!
            print("The license is valid!")
            license_key = result[0]
            print("License expires: " + str(license_key.expires))
            print("Restart bot now")
            print()

            # saving license file to disk
            with open('checkerlicensefile.skm', 'w') as f:
                f.write(result[0].save_as_string())

    @staticmethod
    def auth_user():
        try:
            # read license file from file
            with open('checkerlicensefile.skm', 'r') as f:
                license_key = LicenseKey.load_from_string(RSAPubKey, f.read(), 30)

                if license_key == None or not Helpers.IsOnRightMachine(license_key):
                    print("NOTE: This license file does not belong to this machine.")
                else:
                    print("Logged in")
                    print("License expires: " + str(license_key.expires))
                    print()
                    return True
        except Exception:
            print("You have to register license first.")

    @staticmethod
    def checker(thread, max_froud_score, max_black_lists, proxy_chunk, proxy_type):
        if os.path.exists("CheckedProxy.csv") is False:
            with open("CheckedProxy.csv", "w") as f:
                csv_writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                csv_writer.writerow(['Proxy', 'IP', 'FraudScore', 'CountryCode', 'Region', 'City', 'RecentAbuse', 'Blacklists'])

        with open("api_key.txt") as fl:
            flines = fl.readlines()
        api_key = flines[0]
        ip_checker = pydnsbl.DNSBLIpChecker()

        fraud_scores = []
        country_codes = []
        regions = []
        cities = []
        blacklisted_list = []
        proxies_list = []
        ips = []
        isp_list = []
        bot_status_list = []
        if_proxy_list = []
        vpn_list = []
        recent_abuse_list = []
        tor_list = []

        for step, pline in enumerate(proxy_chunk):
            proxies = {}
            try:
                pline = pline.replace("http://", "").replace("https://", "").replace("\n", "")

                if proxy_type == 0:  # https ip:port http
                    raw = pline.split(":")
                    proxies = {
                        'https': f"https://{raw[0]}:{raw[1]}",
                        'http': f"http://{raw[0]}:{raw[1]}"

                    }

                if proxy_type == 1:  # https ip:port:user:pass
                    raw = pline.split(":")
                    proxies = {
                        'https': f"https://{raw[2]}:{raw[3]}@{raw[0]}:{raw[1]}",
                        'http': f"http://{raw[2]}:{raw[3]}@{raw[0]}:{raw[1]}"

                    }

                if proxy_type == 2:  # https user:pass:ip:port
                    raw = pline.split(":")
                    proxies = {
                        'https': f"https://{raw[0]}:{raw[1]}@{raw[2]}:{raw[3]}",
                        'http': f"http://{raw[0]}:{raw[1]}@{raw[2]}:{raw[3]}"

                    }

                if proxy_type == 3:  # socks ip:port
                    raw = pline.split(":")
                    proxies = {
                        'https': f'socks5://{raw[0]}:{raw[1]}',
                        'http': f'socks5://{raw[0]}:{raw[1]}',
                    }

                if proxy_type == 4:  # socks5 ip:port:user:pass
                    raw = pline.split(":")
                    proxies = {
                        'https': f"socks5://{raw[2]}:{raw[3]}@{raw[0]}:{raw[1]}",
                        'http': f"socks5://{raw[2]}:{raw[3]}@{raw[0]}:{raw[1]}",

                    }

                if proxy_type == 5:  # user:pass:ip:port
                    raw = pline.split(":")
                    proxies = {
                        'https': f"socks5://{raw[0]}:{raw[1]}@{raw[2]}:{raw[3]}",
                        'http': f"socks5://{raw[0]}:{raw[1]}@{raw[2]}:{raw[3]}"

                    }
                # print(proxies)
                print(f"[INFO] Thread: {thread}-{step} checking proxy: {pline}")
                response = requests.get('http://jsonip.com', proxies=proxies)
                # print(response.content)
                ip = response.json()['ip']
                print(f"[INFO] Thread: {thread}-{step} ip checked for proxy: {pline}, ip: {ip}")

                response = requests.get(f'https://ipqualityscore.com/api/json/ip/{api_key}/' + ip +
                                        '?strictness=0&allow_public_access_points=true&fast=true&lighter_'
                                        'penalties=true&mobile=true')
                data = json.loads(response.content)

                fraud_score = data['fraud_score']
                country_code = data['country_code']
                region = data['region']
                city = data['city']
                isp = data['ISP']
                bot_status = data['bot_status']
                check = ip_checker.check(ip)
                if_proxy = data['proxy']
                vpn = data['vpn']
                tor = data['tor']
                recent_abuse = data['recent_abuse']
                check = str(check)
                raw = check.split("<DNSBLResult: ")
                raw2 = raw[1].split(" ")
                blacklisted = raw2[2].replace(">", "")
                how_many = blacklisted.replace("/56)", "").replace("(", "").replace("/50)", "")

                print(f"[INFO] Thread: {thread}-{step} proxy: {pline} has been checked")
                print(f"[INFO] Thread: {thread}-{step} proxy: {pline} basic info: \n-Fraud score: {fraud_score}"
                      f"\n-Blacklisted: {blacklisted}")

                if max_froud_score == 0 and max_black_lists != 0:
                    max_froud_score = 1000

                if max_froud_score != 0 and max_black_lists == 0:
                    max_black_lists = 1000

                if max_froud_score != 0 and max_black_lists != 0:
                    if fraud_score <= max_froud_score and int(how_many) <= max_black_lists:
                        with open("CheckedProxy.csv", "a", newline="") as f:
                            csv_writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                            csv_writer.writerow([pline, ip, fraud_score, country_code, region, city, recent_abuse, blacklisted])
                            print(f"[INFO] Thread: {thread}-{step} proxy: {pline} saved")

                if max_froud_score == 0 and max_black_lists == 0:
                    with open("CheckedProxy.csv", "a", newline="") as f:
                        csv_writer = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
                        csv_writer.writerow([pline, ip, fraud_score, country_code, region, city, recent_abuse, blacklisted])
                        print(f"[INFO] Thread: {thread}-{step} proxy: {pline} saved")

            except Exception as e:
                # import traceback
                # traceback.print_exc()
                print(f"[ERROR] Thread {thread}-{step}: {e}")
                sleep(2)

        print(f"[INFO] Thread {thread}: done")
        done_threads.append(1)


started = False
xd_threads = 0
configs_error = False
if __name__ == '__main__':
    print(30 * "-")
    print("Welcome to LumiskProxyChecker")
    print(30 * "-")

    checker = ProxyChecker()
    print("1. Register license")
    print("2. Log in")
    first_lvl_answer = str(input())
    first_lvl_answer = int(first_lvl_answer)

    if first_lvl_answer == 1:
        while True:
            print("Enter license")
            lic = str(input())
            if lic == "exit":
                break
            else:
                checker.validate_license(lic)
                break
    elif first_lvl_answer == 2:
        # auth_ = checker.auth_user()
        auth_ = True
        if auth_ is True:
            while True:
                print("Press 1 to start")
                print("Press 2 to create apis file")
                print(30 * "-")
                print()

                answer = str(input())
                answer = int(answer)

                if answer == 2:
                    while True:
                        print("Enter Api key for proxy checking api")
                        sms_api_key = str(input())
                        if sms_api_key == "exit":
                            break

                        with open("api_key.txt", "a+") as ap_file:
                            ap_file.write(sms_api_key)
                        ap_file.close()
                        print("File has been created. Restart bot now.")
                        break

                elif answer == 1:
                    exit_ = 0
                    config_list = []
                    config_list.clear()
                    while True:
                        if xd_threads == len(done_threads):
                            done_threads = []
                            xd_threads = 0
                            started = False

                        if started is not True:
                            while True:
                                print("Use saved configuration. Yes or No")

                                use_saved_config = str(input())
                                if use_saved_config == "exit":
                                    break
                                if use_saved_config == "Yes" or use_saved_config == "yes":
                                    print("List of saved config files:")
                                    try:
                                        for conf_file in os.listdir("CheckerConfigs"):
                                            print(f"- {conf_file}")
                                    except Exception:
                                        print("[ERROR] You have no configs yet")
                                        configs_error = True
                                        break

                                    print("Enter configuration file name")
                                    chosen_conf_file_name = str(input())
                                    if chosen_conf_file_name == "exit":
                                        exit_ = 1
                                        break
                                    try:
                                        with open(f"CheckerConfigs/{chosen_conf_file_name}", "r") as ccfn:
                                            cfn_lines = ccfn.readlines()
                                            print(f"[INFO] Config file content: {cfn_lines}")
                                            break
                                    except:
                                        print(f"[INFO] This file doesn't exists.")

                                elif use_saved_config == "No" or use_saved_config == "no":
                                    break
                            if configs_error:
                                configs_error = False
                                break
                            if use_saved_config == "exit" or exit_ == 1:
                                exit_ = 0
                                break

                            if use_saved_config == "Yes" or use_saved_config == "yes":
                                threads = int(cfn_lines[0].replace("\n", ""))
                            else:
                                while True:
                                    print("How many threads?")
                                    threads = str(input())
                                    if threads == "exit":
                                        break
                                    try:
                                        threads = int(threads)
                                        config_list.append(str(threads))
                                        break
                                    except:
                                        print("[ERROR] Incorrect data")
                            if threads == "exit":
                                break

                            if use_saved_config == "Yes" or use_saved_config == "yes":
                                how_many = int(cfn_lines[1].replace("\n", ""))
                            else:
                                while True:
                                    print("How many lines per thread?")
                                    how_many = str(input())
                                    if how_many == "exit":
                                        break
                                    else:
                                        try:
                                            how_many = int(how_many)
                                            config_list.append(str(how_many))
                                            break
                                        except:
                                            print("[INFO] Incorrect data")

                            if use_saved_config == "Yes" or use_saved_config == "yes":
                                proxy_file = str(cfn_lines[2].replace("\n", ""))
                            else:
                                print("Proxy file path.")
                                proxy_file = str(input())
                                if proxy_file == "exit":
                                    break
                                else:
                                    while True:
                                        try:
                                            with open(proxy_file) as pro_f:
                                                prox_lines = pro_f.readlines()

                                                if len(prox_lines) == 0:
                                                    print('Proxy file is empty.')
                                                    break
                                                else:
                                                    config_list.append(proxy_file)
                                                    break
                                        except Exception:
                                            print("This file does not exists")
                                            break

                            if use_saved_config == "Yes" or use_saved_config == "yes":
                                max_froud_score = int(cfn_lines[3].replace("\n", ""))
                            else:
                                while True:
                                    print("Max froud score. Set to 0 to ignore.")
                                    max_froud_score = str(input())
                                    if max_froud_score == "exit":
                                        break
                                    try:
                                        max_froud_score = int(max_froud_score)
                                        config_list.append(str(max_froud_score))
                                        break
                                    except:
                                        print("[ERROR] Incorrect data")

                            if use_saved_config == "Yes" or use_saved_config == "yes":
                                max_black_lists = int(cfn_lines[4].replace("\n", ""))
                            else:
                                while True:
                                    print("Max black lists. Set to 0 to ignore.")
                                    max_black_lists = str(input())
                                    if max_black_lists == "exit":
                                        break
                                    try:
                                        max_black_lists = int(max_black_lists)
                                        config_list.append(str(max_black_lists))
                                        break
                                    except:
                                        print("[ERROR] Incorrect data")

                            if use_saved_config == "Yes" or use_saved_config == "yes":
                                proxy_type = int(cfn_lines[5].replace("\n", ""))
                            else:
                                while True:
                                    print("Choose proxy type:")
                                    print("0. http ip:port")
                                    print("1. http ip:port:user:pass")
                                    print("2. http user:pass:ip:port")
                                    print("3. socks5 ip:port")
                                    print("4. socks5 ip:port:user:pass")
                                    print("5. socks5 user:pass:ip:port")
                                    proxy_type = str(input())
                                    if proxy_type == "exit":
                                        break
                                    try:
                                        proxy_type = int(proxy_type)
                                        config_list.append(str(proxy_type))
                                        break
                                    except:
                                        print("[ERROR] Incorrect data")

                            if use_saved_config == "No" or use_saved_config == "no":
                                while True:
                                    print("Do you want to save config? Yes or no.")
                                    save_config = str(input())
                                    if save_config == "exit":
                                        break
                                    elif save_config == "Yes" or save_config == "yes":
                                        print("Enter file name")
                                        config_file_name = str(input())
                                        if not os.path.exists("CheckerConfigs"):
                                            os.makedirs("CheckerConfigs")
                                        with open(f"CheckerConfigs/{config_file_name}.txt", "a+") as config_file:
                                            for config in config_list:
                                                config_file.write(config)
                                                config_file.write("\n")
                                        config_file.close()
                                        config_list.clear()
                                        break
                                    elif save_config == "No" or save_config == "no":
                                        break
                                if save_config == "exit":
                                    break

                            all_proxies = []
                            with open(proxy_file) as f:
                                lines = f.readlines()
                                for line in lines:
                                    line_ = line.strip("\n")
                                    all_proxies.append(line_)

                            proxy_chunk_list = []

                            start = 0
                            end = how_many
                            for i in range(threads):
                                proxy_chunk_list = all_proxies[start:end]

                                #checker.checker(i, max_froud_score, max_black_lists, proxy_chunk_list)
                                threading.Thread(target=checker.checker,
                                                 args=(i, max_froud_score, max_black_lists, proxy_chunk_list, proxy_type)).start()
                                start += how_many
                                end += how_many
                            xd_threads = threads
                            started = True