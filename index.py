from bs4 import BeautifulSoup
from urllib2 import urlopen
from datetime import datetime
from datetime import timedelta
import pytz
import icalendar
import os
import re
import sys

# Hack found on http://stackoverflow.com/questions/2276200/changing-default-encoding-of-python
reload(sys)
sys.setdefaultencoding('UTF8')

# I don't like typing
strftime = datetime.strftime
strptime = datetime.strptime


# This was the original way I saved the start and end times
# Returns a datetime object as an epoch, in seconds
# @datetimeObject: A datetime object
def toEpoch(dateTimeObject):
    if dateTimeObject.tzinfo is None:
        epochStart = datetime(1970, 1, 1)
    else:
        epochStart = datetime(1970, 1, 1, tzinfo = centralTimezone)

    return (dateTimeObject - epochStart).total_seconds()


# Returns the user name across OS types
def getUserName():
    envs = os.environ
    if envs.has_key('USER'):
        return envs['USER']

    if envs.has_key('USERNAME'):
        return envs['USERNAME']

# Returns the user's home directory
def getHomeDir():
    return os.path.expanduser('~' + getUserName())


# Shortcut to icalendar's to_ical for dates function
def icalDatetime(dateTimeObject):
    return icalendar.vDatetime(dateTimeObject).to_ical()


# Shortcut for a cleanstring function that also replaces mdashes
def cleanString(inputString):
    try:
        return str(re.sub('\xe2\x80\x93', '-', inputString.encode('utf-8'))).strip()
    except:
        print "Could not clean string %s \n %s" % (inputString, Exception.message)


def getSchedule (soup):
    sessions = []
    sessionDate = datetime(2016, 8, 11, tzinfo = centralTimezone)
    maxHour = 0

    sessionDetails = soup.find('div', 'sessions-container')('div', 'uv-card--session')

    for thisSession in sessionDetails:
        # Session Name
        sessionName = cleanString(thisSession.find('h2', 'uv-card__title').contents[0])
        # Session Track; default to 'General'
        trackInfo = thisSession.find('div', 'tracks__name')
        if trackInfo is not None:
            sessionTrack = cleanString(''.join(trackInfo.contents)).strip()
        else:
            sessionTrack = 'General'

        # Session start and end
        sessionTimes = thisSession.find_all('span', 'session__time', True)
        # Convert the times to a time object, so we can also include the date
        startTime = strptime(cleanString(sessionTimes[0].contents[0]), '%H:%M')
        endTime = strptime(cleanString(sessionTimes[1].contents[0]), '%H:%M')

        # Detect when we're at the start of a new day
        if startTime.hour >= maxHour:
            maxHour = startTime.hour
        else:
            maxHour = startTime.hour
            sessionDate += timedelta(days = 1)

        # Store the entire date for the start and end
        sessionStart = icalDatetime(sessionDate.replace(hour = startTime.hour, minute = startTime.minute))
        sessionEnd = icalDatetime(sessionDate.replace(hour = endTime.hour, minute = endTime.minute))

        # Session Room Name
        sessionLocation = thisSession('span', 'session__location')
        if sessionLocation != []:
            sessionLocation = cleanString(sessionLocation[0].contents[0])
        else:
            sessionLocation = ''

        # Session speakers and info
        speakers = []
        sessionSpeakers = thisSession('div', 'uv-shortcard--speaker')
        if sessionSpeakers != []:
            for thisSpeaker in sessionSpeakers:
                speakerName = cleanString(thisSpeaker('div', 'uv-shortcard__title')[0].contents[0])
                speakerInfo = ', '.join({cleanString(', '.join(subtitle.contents)) for subtitle in thisSpeaker('div', 'uv-shortcard__subtitle')})
                speakers.append(speakerName + ', ' + speakerInfo.strip())

        # Add the session to the session list
        sessions.append({
            'Name': sessionName,
            'Track': sessionTrack,
            'Start': sessionStart,
            'End': sessionEnd,
            'Location': sessionLocation,
            'Speakers': '; '.join(speakers)
        })

    return sessions


siteURL = "http://theanalyticssummit.com"
centralTimezone = pytz.timezone('US/Central')
today = datetime.now(centralTimezone)
hotelLocation = "Omni Nashville Hotel, 250 5th Avenue South Nashville TN 37203 US"
# Export location is in the user's desktop directory
calendarOutputFile = '/tmp/exportedCalendar.ics'

outputPath = os.path.dirname(calendarOutputFile)

# Create the path if it doesn't exist
if os.path.exists(outputPath) is False:
    os.mkdir(outputPath)

# Populate the session schedule
sessionsDetail = getSchedule(BeautifulSoup(urlopen(siteURL).read(), "html.parser"))

cal = icalendar.Calendar()
# Required for the spec
cal.add('prodid', '-//Python iCalendar entry//mxm.dk//')
cal.add('version', '2.0')
cal.add('dtstamp', today)

for session in sessionsDetail:
    event = icalendar.Event()
    event.add('dtstart', icalendar.vDatetime.from_ical(session['Start']))
    event.add('dtend', icalendar.vDatetime.from_ical(session['End']))
    event.add('summary', session['Name'] + ' - ' + session['Location'])
    # Using the hotel location, so Maps directions will show up properly :)
    event.add('location', hotelLocation)
    event.add('description', 'Track: ' + session['Track'] + '\n' + session['Speakers'])
    cal.add_component(event)

try:
    with open(calendarOutputFile, mode = 'w') as ical:
        ical.write(cal.to_ical())

    print 'The calendar was exported to %s' % calendarOutputFile
except:
    print 'Could not export the file %s' % Exception.message
