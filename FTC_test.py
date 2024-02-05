# Importing libraries
import time
import requests
import pandas as pd
import numpy as np

import imaplib
import email
import os
import csv

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders

import smtplib
user = "brayden.msherrod@gmail.com"
password = "---------"

svdir = '/Users/braydensherrod/Desktop'

#eventcode = 'USTXCECMPJHNS'
eventcode = 'FTCCMP1JEMI'
level = 'qual'

def get_mail(eventcode, level):
    #URL for IMAP connection
    imap_url = 'imap.gmail.com'

    # Connection with GMAIL using SSL
    my_mail = imaplib.IMAP4_SSL(imap_url)
    
    # Log in using your credentials
    my_mail.login(user, password)

    # Select the Inbox to fetch messages
    my_mail.select('Inbox')

    typ, msgs = my_mail.search(None, '(SUBJECT "FTC-SERVER" UNSEEN)') #UNSEEN
    msgs = msgs[0].split()

    for emailid in msgs:
        print("Found Mail")
        resp, data = my_mail.fetch(emailid, "(RFC822)")
        email_body = data[0][1]
        raw_email_string = email_body.decode('utf-8')
        m = email.message_from_string(raw_email_string)


        if m.get_content_maintype() != 'multipart':
            if 'setup' in m['subject'].lower():
                print("Running Setup")
                setup_matches()
                send_email(m['from'], 'Starting Position Sheet', 'Here is the initial position sheet to fill in with side data.', str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
            elif 'match' in m['subject'].lower():
                print("Running Match Retrieval")
                #matchNum = get_matchNum()
                send_email(m['from'], 'Current Position Sheet', 'Here is the most up-to-date position sheet.', str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
            elif 'analysis' in m['subject'].lower():
                print("Running Analysis")
                update_analysis()
                #matchNum = get_matchNum()
                send_email(m['from'], 'Current Analysis Sheet', 'Here is the most up-to-date analysis sheet', str(eventcode) + '-' + str(level) + '-' + 'analysis.csv')
            elif 'stop' in m['subject'].lower():
                print("Running stop Command")
                send_email(m['from'], 'Stopping Server', 'Here is the most up-to-date analysis sheet.', str(eventcode) + '-' + str(level) + '-' + 'analysis.csv')
                return 0
        else:
            for part in m.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue

                filename=part.get_filename()
                print(filename)
                if filename is not None:
                    sv_path = os.path.join(svdir, filename)
                    # if not os.path.isfile(sv_path):
                    # outfile = svdir + '/' +str(eventcode) + '-' + str(level) + '-' + 'matches.csv'
                    
                    fp = open(sv_path, "wb")
                    fp.write(part.get_payload(decode=True))
                    fp.close()
                    df = pd.read_csv(sv_path)
                    df.dropna()
                    df.to_csv(sv_path, header=True, index=False)
            #update_matches()
                    #matchNum = get_matchNum()
                    send_email(m['from'], 'Matches were updated', 'Here is the updated position sheet.', str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
    return 1
                

def send_email(to, subject, content, filename):
    from_addr = 'brayden.msherrod@gmail.com'
    msg = MIMEMultipart()
    msg['From'] = from_addr
    msg['To'] = to
    msg['Subject'] = subject
    body = MIMEText(content, 'plain')
    msg.attach(body)
    
    if filename != '':
        filename = svdir + '/' + filename
        attachment = open(filename, 'rb')
        attachment_pkg = MIMEBase('application', 'octet-stream')
        attachment_pkg.set_payload((attachment.read()))
        encoders.encode_base64(attachment_pkg)
        attachment_pkg.add_header('Content-Disposition', "attachment; filename= " + os.path.basename(filename))
        msg.attach(attachment_pkg)

    text = msg.as_string()
    server = smtplib.SMTP('smtp.gmail.com.', 587)
    server.starttls()
    server.login(user, password)
    server.send_message(msg, from_addr=from_addr, to_addrs=[to])



'''
For the auto placements it makes a 5x5 grid starting at top left of online view or watching view.
           [G] [L] [G] [L] [G]  
L   Blue2  [L] [M] [H] [M] [L]  Red2 R
           [G] [H] [G] [H] [G]
R   Blue1  [L] [M] [H] [M] [L]  Red1 L
           [G] [L] [G] [L] [G]

'''
autoScoreGuide = [ [2,3,2,3,2],
                  [3,4,5,4,3],
                  [2,5,2,5,2],
                  [3,4,5,4,3],
                  [2,3,2,3,2],]

# Team listings
def get_team_names(eventcode):
    # teamNumber=14361
    t = requests.get('http://ftc-api.firstinspires.org/v2.0/2022/teams?eventCode='+ str(eventcode), auth=('braydensherrod','CB4CA2DF-BA18-42B2-9C3D-DE246FE992E4'))
    df = pd.DataFrame(columns=['TeamNumber', 'TeamName'])
    for team in t.json().get("teams"):
        teamNum = team.get("teamNumber")
        teamName = team.get("nameShort")
        row  = pd.DataFrame([(teamNum, teamName)],columns=['TeamNumber', 'TeamName'])
        df = pd.concat([df, row], ignore_index=True)
    return df
        


# Match Overall Scores
def get_match_team_nums(eventcode, level, matchList=pd.DataFrame, start=0):
    m = requests.get('http://ftc-api.firstinspires.org/v2.0/2022/schedule/' + str(eventcode) +'/' + str(level) + '/hybrid?start=' + str(start) + '&end=999', auth=('braydensherrod','CB4CA2DF-BA18-42B2-9C3D-DE246FE992E4'))
    teamSpots = pd.DataFrame(columns=['Match', 'AllianceSpot', 'TeamNumber', 'Win'])
    if matchList.empty:
        matchList = pd.DataFrame(columns=['Match', 'TeamNumber', 'AllianceColor', 'Side(l/r)'])
    for match in m.json().get("schedule"):
        matchNum = match.get("matchNumber")
        redWins = match.get("redWins")
        blueWins = match.get("blueWins")
        for team in match.get("teams"):
            teamNum = team.get("teamNumber")
            allianceSpot = team.get("station")
            if allianceSpot[:-1] == 'Red':
                allianceWin = redWins
            else:
                allianceWin = blueWins
            team_row = pd.DataFrame([(matchNum, allianceSpot, teamNum, allianceWin)],columns=['Match', 'AllianceSpot', 'TeamNumber', 'Win'])
            teamSpots = pd.concat([teamSpots, team_row], ignore_index=True)
            match_row = pd.DataFrame([(matchNum, teamNum, allianceSpot[:-1], '')],columns=['Match', 'TeamNumber', 'AllianceColor', 'Side(l/r)'])
            matchList = pd.concat([matchList, match_row], ignore_index=True)
    return (teamSpots, matchList)
            


def calcAutoCones(field, side):
    flag = False
    autoScore = 0
    contest = 0
    start = 0
    end = 3
    if side == 1:
        start = 2
        end = 5
    for row in range(start, end):
        for junction in range(len(field[row])):
            for cone in range(len(field[row][junction])):
                if field[row][junction][cone] == 'MY_CONE':
                    if (row == 2):
                        flag = True
                    else:
                        autoScore += autoScoreGuide[row][junction]
                    if (row == 1 and junction) == 2 or (row == 3 and junction == 2):
                        contest = 1
    return (autoScore, contest, flag)



# Match Detailed Scores
def get_score_detail(eventcode, level):
    flagged = []
    s = requests.get('http://ftc-api.firstinspires.org/v2.0/2022/scores/' + str(eventcode)+ '/' + str(level) + '?end=999', auth=('braydensherrod','CB4CA2DF-BA18-42B2-9C3D-DE246FE992E4'))
    matches = pd.DataFrame(columns=['Match', 'AllianceSpot','AllianceAuto', 'AlliancePrePen', 'AlliancePenalty', 'AllianceAutoCones', 'AllianceDcCones', 'AllianceOwnedJunc'])
    autoScores = pd.DataFrame(columns=['Match', 'AllianceColor', 'Side(l/r)','AutoScore', 'Left', 'Right', 'Contest'])
    for match in s.json().get("MatchScores"):
        matchNum = match.get("matchNumber")
        for alliance in match.get("alliances"):
            
            color = alliance.get("alliance")
            park1 = alliance.get("robot1Auto")
            park2 = alliance.get("robot2Auto")
            allianceAuto = alliance.get("autoPoints")
            alliancePrePen = alliance.get("prePenaltyTotal")
            alliancePenalty = alliance.get("penaltyPointsCommitted")
            allianceAutoCones = sum(alliance.get("autoJunctionCones"))
            allianceDcCones = sum(alliance.get("dcJunctionCones"))
            allianceOwned = alliance.get("ownedJunctions")
            if park1 == 'SIGNAL_ZONE':
                park1 = True
            else:
                park1 = False
            if park2 == 'SIGNAL_ZONE':
                park2 = True
            else:
                park2 = False

            autoScoreLeft, autoScoreRight = 0, 0
            contestLeft, contestRight = 0, 0
            flagLeft, flagRight = False, False
            field = alliance.get("autoJunctions")
            if color == 'Blue':
                autoScoreLeft, contestLeft, flagLeft = calcAutoCones(field, 2)
                autoScoreRight, contestRight, flagRight = calcAutoCones(field, 1)
            else:
                autoScoreRight, contestRight, flagRight = calcAutoCones(field, 2)
                autoScoreLeft, contestLeft, flagLeft = calcAutoCones(field, 1)
            if flagLeft or flagRight:
                flagged.append(matchNum)
            
            new_match_rows = pd.DataFrame([(matchNum, color + '1', park1, allianceAuto, alliancePrePen, alliancePenalty, allianceAutoCones, allianceDcCones, allianceOwned),
                                    (matchNum, color + '2', park2, allianceAuto, alliancePrePen, alliancePenalty, allianceAutoCones, allianceDcCones, allianceOwned)],
                                    columns=['Match', 'AllianceSpot','AutoPark', 'AllianceAuto', 'AlliancePrePen', 'AlliancePenalty', 'AllianceAutoCones', 'AllianceDcCones', 'AllianceOwnedJunc'])
            matches =pd.concat([matches, new_match_rows], ignore_index = True)
            new_autoScore_rows = pd.DataFrame([(matchNum, color, 'l', autoScoreLeft, 1, 0, contestLeft),
                                                (matchNum, color, 'r', autoScoreRight, 0, 1, contestRight)],
                                                columns=['Match', 'AllianceColor', 'Side(l/r)', 'AutoScore', 'Left', 'Right', 'Contest'])
            autoScores = pd.concat([autoScores, new_autoScore_rows], ignore_index=True)
    return (matches, autoScores, flagged)



def setup_matches():
    team_spots, match_team = get_match_team_nums(eventcode, level)
    match_team.to_csv('/Users/braydensherrod/Desktop/' + str(eventcode) + '-' + str(level) + '-' + 'matches.csv', header=True, index=False)

# def get_matchNum():
#     df = pd.read_csv('/Users/braydensherrod/Desktop/' + str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
#     # index_df = df['Side(l/r)'] == ''
#     # index = index_df.index[0]
#     lastUpdateMatch = df[df['Side(l/r)'] == '']['Match'].values[0]
#     return lastUpdateMatch

# def update_matches():
#     df = pd.read_csv('/Users/braydensherrod/Desktop/' + str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
#     index_df = df['Side(l/r)'] == ''
#     index = index_df.index[0]
#     startMatch = df['Match'].iloc[index] + 1
#     df = df.iloc[:index+4]
#     team_spots, match_team = get_match_team_nums(eventcode, level, df, startMatch)
#     match_team.to_csv('/Users/braydensherrod/Desktop/' + str(eventcode) + '-' + str(level) + '-' + 'matches.csv', header=True, index=False)
#     print(match_team)

def update_analysis():
    side_labels = pd.read_csv('/Users/braydensherrod/Desktop/' + str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
    # index_df = np.where(side_labels['Side(l/r)'] == '', side_labels['Match'], '')
    # index = index_df.index[0]
    # startMatch = side_labels['Match'].iloc[index] + 1
    detailed_matches, rawAutoScores, flagged = get_score_detail(eventcode, level)
    if len(flagged) > 0:
        send_email('bman877@icloud.com', 'FLAGGED MACTHES', 'These are the flagged matches.\n' + str(flagged), str(eventcode) + '-' + str(level) + '-' + 'matches.csv')
    team_spots, match_team = get_match_team_nums(eventcode, level)
    new_table = pd.merge(team_spots, detailed_matches, on=['Match', 'AllianceSpot'])
    print(rawAutoScores)
    print(side_labels)
    labeledAutoScore = pd.merge(rawAutoScores, side_labels, on=['Match', 'AllianceColor', 'Side(l/r)'])
    #print(labeledAutoScore)
    new_table = pd.merge(new_table, labeledAutoScore, on=['Match', 'TeamNumber'])

    names = get_team_names(eventcode)

    named_table = pd.merge(new_table, names, on=['TeamNumber'])
    updatedRowIndex = len(named_table['Side(l/r)'])-1
    named_table = named_table.loc[0:updatedRowIndex]
    named_table['AutoScore'] = named_table['AutoScore'] + np.where(named_table['AutoPark']== True, 20, 0)
    named_table['AutoScore'] = np.where(named_table['AutoScoreOverride']!= -1, named_table['AutoScoreOverride'], named_table['AutoScore'])
    named_table = named_table.drop(columns=['AutoScoreOverride', 'AllianceColor', 'AllianceSpot', 'Side(l/r)'])
    named_table = named_table.infer_objects()
    p_table = pd.pivot_table(named_table, index=['TeamNumber'], values=['AutoScore', 'Left', 'Right', 'AutoPark', 'Contest', 'AllianceAuto', 'AlliancePrePen', 'AlliancePenalty', 'Win', 'AllianceAutoCones', 'AllianceDcCones', 'AllianceOwnedJunc', 'TeamName'], aggfunc= {'AutoScore': 'mean', 'Left': 'mean', 'Right': 'mean', 'AutoPark': 'mean', 'Contest': 'mean', 'AllianceAuto': 'mean', 'AlliancePrePen': 'mean', 'AlliancePenalty': 'mean', 'Win':'mean', 'AllianceAutoCones': 'mean', 'AllianceDcCones': 'mean', 'AllianceOwnedJunc':'mean', 'TeamName':pd.Series.mode}) #, 'TeamName':pd.Series.mode
    p_table = p_table.reindex(columns=['AutoScore', 'Left', 'Right', 'AutoPark', 'Contest', 'AllianceAuto', 'AlliancePrePen', 'AlliancePenalty', 'Win', 'AllianceAutoCones', 'AllianceDcCones', 'AllianceOwnedJunc', 'TeamName'])
    p_table = p_table.sort_values('AutoScore', ascending=False)
    p_table['AutoScore'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AutoScore']], index = p_table.index)
    p_table['Left'] = pd.Series(["{0:.2f}%".format(val * 100) for val in p_table['Left']], index = p_table.index)
    p_table['Right'] = pd.Series(["{0:.2f}%".format(val * 100) for val in p_table['Right']], index = p_table.index)
    p_table['AutoPark'] = pd.Series(["{0:.2f}%".format(val * 100) for val in p_table['AutoPark']], index = p_table.index)
    p_table['Contest'] = pd.Series(["{0:.2f}%".format(val * 100) for val in p_table['Contest']], index = p_table.index)
    p_table['AllianceAuto'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AllianceAuto']], index = p_table.index)
    p_table['AlliancePrePen'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AlliancePrePen']], index = p_table.index)
    p_table['AlliancePenalty'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AlliancePenalty']], index = p_table.index)
    p_table['Win'] = pd.Series(["{0:.2f}%".format(val * 100) for val in p_table['Win']], index = p_table.index)
    p_table['AllianceAutoCones'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AllianceAutoCones']], index = p_table.index)
    p_table['AllianceDcCones'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AllianceDcCones']], index = p_table.index)
    p_table['AllianceOwnedJunc'] = pd.Series(["{0:.2f}".format(val) for val in p_table['AllianceOwnedJunc']], index = p_table.index)
    
    p_table.to_csv('/Users/braydensherrod/Desktop/' + str(eventcode) + '-' + str(level) + '-' + 'analysis.csv', header=True, index=True)
    print(p_table)

def main():
    while get_mail(eventcode, level):
        time.sleep(15)

main()


