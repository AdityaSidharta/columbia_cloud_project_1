import boto3
import uuid
import datetime

lex = boto3.client('lexv2-runtime')
sqs = boto3.client('sqs')

botID = '4MWEOFDHPK'
botAliasID = 'XQHOMXFVAA'
sessionID = 'testuser'
localeID = 'en_US'
queue_url = 'https://sqs.us-east-1.amazonaws.com/139100004146/Proj1SQS'


def lambda_handler(event, context):
    incoming_msgs = event['messages']
    assert len(incoming_msgs) == 1
    incoming_msg = incoming_msgs[0]
    print("incoming_msg : {}".format(incoming_msg))
    incoming_msg_content = incoming_msg['unstructured']['text']
    
    # Initiate conversation with Lex
    response = lex.recognize_text(
            botId=botID,
            botAliasId=botAliasID,
            localeId=localeID,
            sessionId=sessionID,
            text=incoming_msg_content)
    
    outgoing_msgs = response['messages']
    session_intent = response['sessionState']['intent']
    
    if (session_intent['name'] == 'DiningSuggestionsIntent') & (session_intent['state'] == 'ReadyForFulfillment') & (session_intent['confirmationState'] == 'Confirmed'):
        slots = session_intent['slots']
        result = {k: v['value']['interpretedValue'] for k, v in slots.items()}
        response = sqs.send_message(
              QueueUrl=queue_url,
              DelaySeconds=10,
              MessageAttributes={
                  'Cuisine': {
                      'DataType': 'String',
                      'StringValue': result['Cuisine']
                  },
                  'Date': {
                      'DataType': 'String',
                      'StringValue': result['Date']
                  },
                  'Email': {
                      'DataType': 'String',
                      'StringValue': result['Email']
                  },
                  'Location': {
                      'DataType': 'String',
                      'StringValue': result['Location']
                  },
                  'PeopleNumber': {
                      'DataType': 'String',
                      'StringValue': result['PeopleNumber']
                  },
                  'PhoneNum': {
                      'DataType': 'String',
                      'StringValue': result['PhoneNum']
                  },
                  'Time': {
                      'DataType': 'String',
                      'StringValue': result['Time']
                  }
              },
              MessageBody=str(uuid.uuid4())
          )
    
    if len(outgoing_msgs):
        msgs = []
        for outgoing_msg in outgoing_msgs:
            print("outgoing_msg : {}".format(outgoing_msg))
            outgoing_msg_content = outgoing_msg['content']
            msgs.append({
                    "type": "unstructured",
                    "unstructured": {
                    "id": str(uuid.uuid4()),
                    "text": outgoing_msg_content,
                    "timestamp": datetime.datetime.isoformat(datetime.datetime.now()),
                    }
                })
        return {
                "messages": msgs
            }
    else:
        raise ValueError("Lex has Failed")