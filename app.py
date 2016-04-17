'''
Agile Scrum Pokerbot for Slack

Hosted on AWS Lambda.
'''
import boto3
import logging
from urlparse import parse_qs

# Start Configuration
SLACK_TOKEN = '<insert your Slack token>'
IMAGE_LOCATION = '<insert your image path> (e.g. http://www.my-site.com/images/)'

COMPOSITE_IMAGE = IMAGE_LOCATION + 'composite.png'
VALID_VOTES = {
    0 : IMAGE_LOCATION + '0.png',
    1 : IMAGE_LOCATION + '1.png',
    2 : IMAGE_LOCATION + '2.png',
    3 : IMAGE_LOCATION + '3.png',
    5 : IMAGE_LOCATION + '5.png',
    8 : IMAGE_LOCATION + '8.png',
    13 : IMAGE_LOCATION + '13.png',
    20 : IMAGE_LOCATION + '20.png',
    40 : IMAGE_LOCATION + '40.png',
    100 : IMAGE_LOCATION + '100.png'
}
# End Configuration

logger = logging.getLogger()
logger.setLevel(logging.INFO)

poker_data = {}

def lambda_handler(event, context):
    """The function that AWS Lambda is configured to run on POST request to the
    configuration path. This function handles the main functions of the Pokerbot
    including starting the game, voting, calculating and ending the game.
    """

    req_body = event['body']
    params = parse_qs(req_body)
    token = params['token'][0]

    if token != SLACK_TOKEN:
        logger.error("Request token (%s) does not match expected.", token)
        raise Exception("Invalid request token")

    post_data = {
        'team_id' : params['team_id'][0],
        'team_domain' : params['team_domain'][0],
        'channel_id' : params['channel_id'][0],
        'channel_name' : params['channel_name'][0],
        'user_id' : params['user_id'][0],
        'user_name' : params['user_name'][0],
        'command' : params['command'][0],
        'text' : params['text'][0] if 'text' in params.keys() else None,
        'response_url' : params['response_url'][0]
    }

    if post_data['text'] == None:
        return 'Type */pokerbot help* for pokerbot commands.'

    command_arguments = post_data['text'].split(' ')
    sub_command = command_arguments[0]

    if sub_command == 'start':
        if post_data['team_id'] not in poker_data.keys():
            poker_data[post_data['team_id']] = {}

        poker_data[post_data['team_id']][post_data['channel_id']] = {}

        message = Message('*The poker planning game has started.*')
        message.add_attachment('Vote by typing */pokerbot vote <number>*.', None, COMPOSITE_IMAGE)

        return message.get_message()

    elif sub_command == 'vote':
        if post_data['channel_id'] not in poker_data[post_data['team_id']].keys():
            return "The poker planning game hasn't started yet."

        if len(command_arguments) < 2:
            return "Your vote was not counted. You didn't enter a number."

        vote_sub_command = command_arguments[1]
        vote = None

        try:
            vote = int(vote_sub_command)
        except ValueError:
            return "Your vote was not counted. Please enter a number."

        if vote not in VALID_VOTES:
            return "Your vote was not counted. Please enter a valid poker planning number."

        already_voted = poker_data[post_data['team_id']][post_data['channel_id']].has_key(post_data['user_id'])

        poker_data[post_data['team_id']][post_data['channel_id']][post_data['user_id']] = vote

        if already_voted:
            return "You changed your vote to *%d*." % (vote)
        else:
            return "You voted *%d*." % (vote)

    elif sub_command == 'end':
        if (post_data['team_id'] not in poker_data.keys() or
                post_data['channel_id'] not in poker_data[post_data['team_id']].keys()):
            return "The poker planning game hasn't started yet."

        votes = {}

        for player in poker_data[post_data['team_id']][post_data['channel_id']]:
            player_vote = poker_data[post_data['team_id']][post_data['channel_id']][player]

            if not votes.has_key(player_vote):
                votes[player_vote] = []

            votes[player_vote].append(player)

        poker_data[post_data['team_id']][post_data['channel_id']].clear()

        vote_set = set(votes.keys())

        if len(vote_set) == 1:
            message = Message('*Congratulations!*')
            message.add_attachment('Everyone selected the same number.', 'good', VALID_VOTES.get(vote_set.pop()))

            return message.get_message()
        else:
            message = Message('*No winner yet.* Discuss and continue voting.')

            for vote in votes:
                message.add_attachment(", ".join(votes[vote]), 'warning', VALID_VOTES[vote], true)

            return message.get_message()
    elif sub_command == 'help':
        return 'TODO: help'
    else:
        return 'Invalid command. Type */pokerbot help* for pokerbot commands.'


class Message():
    """Public Slack message

    see `Slack message formatting <https://api.slack.com/docs/formatting>`_
    """

    def __init__(self, text):
        """Message constructor.

        :param text: text in the message
        :param color: color of the Slack message side bar
        """
        self.__message = {}
        self.__message['response_type'] = 'in_channel'
        self.__message['text'] = text

    def add_attachment(self, text, color=None, image=None, thumbnail=False):
        """Add attachment to Slack message.

        :param text: text in the attachment
        :param image: image in the attachment
        :param thumbnail: image will be thubmanail if True, full size if False
        """
        if not self.__message.has_key('attachments'):
            self.__message['attachments'] = []

        attachment = {}
        attachment['text'] = text

        if color != None:
            attachment['color'] = color

        if image != None:
            if thumbnail:
                attachment['thumb_url'] = image
            else:
                attachment['image_url'] = image

        self.__message['attachments'].append(attachment)

    def get_message(self):
        """Get the Slack message.

        :returns: the Slack message in format ready to return to Slack client
        """
        return self.__message
