import sys,os
import re
import json
import requests
from rich.console import Console
from time import sleep
import queue
from queue import Queue
from threading import Thread
import gender_guesser.detector as gender
from rich.theme import Theme
from rich.console import Console

########## IMPORTS ##########
parent_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_folder)
from utils.database import InstagramDatabase
from utils.config import Config

# Ustawienie ścieżki dostępu do pliku nam_dict.txt

gender.DATA_PATH = os.path.join(os.path.dirname(gender.__file__), 'data')
console = Console(theme=Theme({"repr.number": "rgb(41,128,185)"}))

class AccountChecker:
    def __init__(self, db, config):
        self.config = config
        self.db = db
        self.db.create_table_szef()
        proxy = self.config.get('Scraping', 'proxy')
        self.max_attempts = self.config.get('Scraping', 'max_attempts')
        self.threads = int(self.config.get('Scraping', 'threads'))
        self.min_followers = int(self.config.get('Scraping', 'Min_followers'))
        self.proxy = proxy.split(':')
        self.proxy = f'{self.proxy[2]}:{self.proxy[3]}@{self.proxy[0]}:{self.proxy[1]}'
        self.token_usage_count = 0
        self.csrf_token = None

    def get_csrf_token(self):
        if self.token_usage_count % 10 == 0:
            url = "https://www.instagram.com/api/v1/web/data/shared_data/"
            proxy = {
                'http': f'http://{self.proxy}',
                'https': f'http://{self.proxy}',
            }
            for i in range(3):
                try:
                    req = requests.get(url)
                    self.csrf_token = re.findall(r'"csrf_token":"(.*?)"', req.text)[0]
                    return self.csrf_token
                except Exception as e:
                    console.print(f"[bold red]Error fetching CSRF token: {e}[/bold red]")
        else:
            return self.csrf_token

    def get_acc(self):
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT Username, From_user FROM instagram")
        result = cursor.fetchall()
        return result

    def remove_user(self, username):
        try:
            self.db.connection.execute("DELETE FROM instagram WHERE Username=?", (username,))
            self.db.connection.commit()
            console.print(f"[[bold green]Sorted[/bold green]] [bold]{username}removed from database[/bold]")
        except Exception as e:
            pass
    def check_konto(self, user, from_user):
        csrf_token = self.get_csrf_token()
        self.token_usage_count += 1
        cookies = {
            'csrftoken': f'{csrf_token}',
            'mid': 'ZGQHcAAEAAHWDG6mJA0xvPCPMLQN',
            'ig_did': '5A5D7559-960E-43DD-A2AD-2E95FF751F75',
            'datr': 'WcdkZEtVxCSdpvlyQpYiV_oL',
            'dpr': '1',
        }

        proxy = {
            'http': f'http://{self.proxy}',
            'https': f'http://{self.proxy}',
        }

        headers = {
            'authority': 'www.instagram.com',
            'accept': '*/*',
            'accept-language': 'en,pl-PL;q=0.9,pl;q=0.8,fr;q=0.7,pt;q=0.6,ru;q=0.5',
            'cookie': f'csrftoken={csrf_token}; mid=ZGQHcAAEAAHWDG6mJA0xvPCPMLQN; ig_did=5A5D7559-960E-43DD-A2AD-2E95FF751F75; datr=WcdkZEtVxCSdpvlyQpYiV_oL; dpr=1',
            'referer': f'https://www.instagram.com/{user}/',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Google Chrome";v="113.0.5672.92", "Chromium";v="113.0.5672.92", "Not-A.Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-ch-ua-platform-version': '"12.1.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
            'viewport-width': '945',
            'x-asbd-id': '198387',
            'x-csrftoken': f'{csrf_token}',
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': '0',
            'x-requested-with': 'XMLHttpRequest',
        }
            
        params = {
            'username': f'{user}',
        }
        results = []
        for _ in range(int(self.max_attempts)):  # try up to 3 times
            try:
                response = requests.get(
                    'https://www.instagram.com/api/v1/users/web_profile_info/',
                    params=params,
                    cookies=cookies,
                    headers=headers,
                    proxies=proxy
                )
                #print error text

                respo = response.json()
                if respo['data']['user']['edge_followed_by']['count'] > int(self.min_followers):
                    console.print(f"[[bold green]+[/bold green]] [bold] {respo['data']['user']['username']} {respo['data']['user']['full_name']} {respo['data']['user']['edge_followed_by']['count']} {respo['data']['user']['edge_owner_to_timeline_media']['count']} [/bold]")
                    try:
                        full_name = (respo['data']['user']['full_name'])
                        if len(full_name) > 0:
                            try:
                                first_name = full_name.split(' ')[0].strip()
                                d = gender.Detector()
                                predicted_gender = d.get_gender(first_name)
                                print(predicted_gender)
                                if predicted_gender == 'female':
                                    console.print(f"[[bold purple]Kobieta[/bold purple]]: [bold]{respo['data']['user']['username']} {respo['data']['user']['full_name']} {respo['data']['user']['edge_followed_by']['count']} [/bold] ")
                                    results.append((str(respo['data']['user']['username']), str(from_user)))
                                    break
                            except:
                                pass
                        else:
                            break
                    except Exception as e:
                        print(e)
                else:
                    results.append((str(respo['data']['user']['username']), str(from_user)))
                    console.print(f"[[bold red]-[/bold red]][bold] {respo['data']['user']['username']} {respo['data']['user']['full_name']} {respo['data']['user']['edge_followed_by']['count']} [/bold]")
                    break  
            except Exception as e:
                continue
        return results

    def worker(self, results_queue):
        while True:
            try:
                item = self.q.get()  # timeout after 1 second if no item can be retrieved
                if item is None:
                    return  # exit the worker function if the queue is empty
                user, from_user = item
                results = self.check_konto(user, from_user)
                for result in results:
                    results_queue.put((result[0]))
                self.q.task_done()
            except queue.Empty:
                return  # exit the worker function if the queue is empty
   

    async def main(self):
        results_queue = Queue()
        self.users = self.get_acc()

        self.q = Queue()
        threads = []
        num_worker_threads = self.threads

        for i in range(num_worker_threads):
            t = Thread(target=self.worker, args=(results_queue,)) 
            t.setDaemon(True)
            t.start()
            threads.append(t)

        for user, from_user in self.users:
            self.q.put((user, from_user))

        self.q.join()

        for i in range(num_worker_threads):
            self.q.put(None)
        for t in threads:
            t.join()

        while not results_queue.empty():
            try:
                # remove user from database
                username = results_queue.get()  # if your tuple has 3 elements
                self.remove_user(username)
            except ValueError as e:
                print(e)
                pass