#!/usr/bin/env python3
# By LimeCat

import psutil
import time
import operator
import yaml
import os
import sys
import humanize
import qbittorrentapi
import logging
import logging.config
from colorama import Fore, Style, init
from discordwebhook import Discord
from tenacity import retry, stop_after_attempt, after_log, wait_fixed

# Logging Consol + File
os.makedirs("log", exist_ok=True)
logging.config.fileConfig('logging.conf')
logger_globale = logging.getLogger(__name__)
logger = logging.getLogger("qbAutoDelt")
listlog = logging.getLogger('torrentSelection')
init(autoreset=True)

# Connection a l'api de qBit, en cas d'echec retente 20 fois avec un delay de 340 seconds avant de down le script.


@retry(stop=stop_after_attempt(20), after=after_log(logger, logging.WARNING), wait=wait_fixed(340))
def qBit_Connection(logger, cfgGen):

    qbt = qbittorrentapi.Client(
        host=cfgGen["qBittorrent"]["host"], username=cfgGen["qBittorrent"]["user"], password=cfgGen["qBittorrent"]["password"], VERIFY_WEBUI_CERTIFICATE=False)
    try:
        qbt.auth_log_in()
        logger.info(
            f'{Fore.CYAN}Conection with qBittorrent tested OK : Qbittorrent {qbt.app.version}, API {qbt.app.web_api_version}{Style.RESET_ALL}')
    except:
        logger.warning(
            f'{Fore.RED}{Style.BRIGHT}Conection with qBittorrent and Web Api Logging failed{Style.RESET_ALL}')
        raise
    return qbt


# Manage the multipl tags or cat retourn by api


def convert_To_List(string):
    if string:
        st_list = list(string.split(", "))
        return st_list

# Comapare les liste est retourne un boll True si present et False sinon


def list_Contains(List1, List2):
    if (List1 and List2):
        set1 = set(List1)
        set2 = set(List2)
        if set1.intersection(set2):
            return True
        else:
            return False

# Transforme un dico en Tuple et le trie en fonction de la valleur de sa clé


def for_Sorted_Dict(dict1):
    sortedDict = sorted(dict1.items(), key=lambda item: item[1], reverse=True)
    itemCount = 0
    for item in sortedDict:
        itemCount = itemCount + 1
        listlog.info(f"Torrent {str(itemCount)} :: {item} ")
    # backTodict = {k: v for k, v in sortedDict}

# Retourn True si un torrent a un tag ou des condition d'exclusion dans les paramettres


def exclud_Torrent(torrent):

    excludTags = cfgSel["Torrents_Tags"]["exclud"]
    excludCats = cfgSel["Torrents_Category"]["exclud"]
    excludTorrentStatesToExclud = cfgGen["Torrent_States"]["TorrentStatesToExclud"]
    excludSeederCountLimit = cfgSel["countSeeder"]
    minTime = cfgSel["min_SeedTime"] * 60 * 60
    minRatio = cfgSel["min_Ratio"]
    listlog.debug(f"Torrent : {torrent} ")
    if torrent.tags in excludTags:
        return True
    elif torrent.category in excludCats:
        return True
    elif torrent.state in excludTorrentStatesToExclud:
        return True
    elif torrent.num_complete < excludSeederCountLimit:
        return True
    elif torrent.ratio < minRatio:
        return True
    elif seed_Time_Torrent(torrent) < minTime:
        return True


# Défini le temps de seed du torrent, si le Fix de l'api 2.2 est sur True, utilise le temps actif totale (moin precis car ne prend
# pas en compte les potentielle temps ou le tracker et offline, ni le temps de téléchargement pour les torrent qui down lentement
# donc impertaivement prévoir quelque heur de marge dans le réglage pour H&R)
# sinon prend le seedTime réel fourni par la nouvelle API


def seed_Time_Torrent(torrent):
    if cfgGen["fix"]:
        SeedTime = torrent.time_active
    else:
        SeedTime = torrent.seeding_time
    return SeedTime

# défini si il y a des torrent public ou a supp a chaque boucle.


def torrent_Check(torrentsInfo):
    
    minSeedTime = int(cfgGen["autoSupp"]["minSeedTime"]) * 60 * 60
    minSeedUpspeed = int(cfgGen["autoSupp"]["minSeedUpspeed "]) * 1024
    excludTorrentStatesToExclud = cfgGen["Torrent_States"]["TorrentStatesToExclud"]
    tagsPriority = cfgGen["Torrents_Tags"]["priority"]
    torrentData = dict()

    for torrent in torrentsInfo:
        if not torrent.state == "downloading":
            if list_Contains(convert_To_List(torrent.tags), tagsPriority):
                if seed_Time_Torrent(torrent) > minSeedTime:
                    torrentInfo = (torrent.name, torrent.size)
                    torrentData[torrent.hash] = torrentInfo
        else:
            if list_Contains(convert_To_List(torrent.tags), tagsPriority):
                 if torrent.upspeed < minSeedUpspeed:
                    torrentInfo = (torrent.name, torrent.size)
                    torrentData[torrent.hash] = torrentInfo     
    return torrentData


# Suppression des torrent public et torrent tag ou cat Priority sans se souci de l'espace disque.


def supp_Torrent_Auto_Tagged(torrentCheck, torrentsInfo):

    time.sleep(3)
    torrentData = torrentCheck
    
    for torrent in torrentData:
        qbt.torrents_delete(delete_files=True,
                            torrent_hashes=torrent)
        logger.info(
            f'{Fore.YELLOW}{Style.BRIGHT}Script delete: {Fore.WHITE}{torrentSelected[0]}, {Fore.RED}{humanize.naturalsize(sizeTorrent, binary=True)}{Fore.YELLOW} free up.{Style.RESET_ALL}')
        time.sleep(10)


# Prompt confirmation [y/n]


###############################
####        Script        #####
###############################


if __name__ == '__main__':

    # General Config:
    with open('config/GeneralSetting.yml', 'r') as ymlfile:
        cfgGen = yaml.load(ymlfile, Loader=yaml.FullLoader)

    # Main loop
    while True:
        qbt = qBit_Connection(logger, cfgGen)
        torrentsInfo = qbt.torrents_info()
        torrentCheck = torrent_Check(torrentsInfo)
        interval = cfgGen['interval']
        # # For Test:
        # dataScored = score_Torrent(torrentsInfo)
        # for_Sorted_Dict(dataScored)
        supp_Torrent_Auto_Tagged(torrentCheck, torrentsInfo)
        time.sleep(int(interval) * 60)
