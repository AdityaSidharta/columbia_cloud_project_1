from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import boto3
import time

opensearch_host = 'search-project1-fcmtfzdorczceupsri4f5e376y.us-east-1.es.amazonaws.com'
region = 'us-east-1'
port = 443
index_name = 'restaurant'
queue_name = 'Proj1SQS'
size = 3
max_timeout = 60
sleep_time = 10


def lambda_handler(event, context):
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=queue_name)
    messages = queue.receive_messages(MessageAttributeNames=['All'])
    if len(messages):
        for message in messages:
            print("Processing message {}".format(message.message_id))

            cuisine = message.message_attributes.get('Cuisine').get('StringValue')
            date = message.message_attributes.get('Date').get('StringValue')
            email = message.message_attributes.get('Email').get('StringValue')
            people_number = message.message_attributes.get('PeopleNumber').get('StringValue')
            booking_time = message.message_attributes.get('Time').get('StringValue')

            print("Receiving message from SQS - Cuisine : {}, Date : {}, Email : {}, People Number : {}, Booking Time : {}".format(
                cuisine,
                date,
                email,
                people_number,
                booking_time
            ))

            credentials = boto3.Session().get_credentials()
            auth = AWSV4SignerAuth(credentials, region)
            opensearch = OpenSearch(
                hosts = [{'host': opensearch_host, 'port': port}],
                http_auth = auth,
                use_ssl = True,
                verify_certs = True,
                connection_class = RequestsHttpConnection
            )

            query = {
            'size': size,
            'query': {
                'multi_match': {
                'query': cuisine,
                'fields': ['cuisine']
                }
            }
            }

            response = opensearch.search(
                body = query,
                index = index_name
            )

            if response['hits']:
                restaurant_ids = [hits['_source']['restaurant_id'] for hits in response['hits']['hits']]
                print("Receiving restaurant_ids from OpenSearch : {}".format(restaurant_ids))
            else:
                raise ValueError("Open Search Failed")

            dynamodb = boto3.client("dynamodb")

            locations = []
            names = []

            assert len(restaurant_ids)

            for restaurant_id in restaurant_ids:

                response = dynamodb.get_item(
                    TableName='cloud1-db',
                    Key={
                        'id': {'S': restaurant_id},
                    }
                )

                try:
                    location = response['Item']['address']['S']
                    name = response['Item']['name']['S']
                    locations.append(location)
                    names.append(name)
                    print("restaurant_id : {}".format(restaurant_id))
                    print("name : {}".format(name))
                    print("location : {}".format(location))
                except:
                    raise ValueError("DynamoDB Failed")

            sns = boto3.client("sns")
            response = sns.list_topics()
            topic_arn = response["Topics"][0]['TopicArn']
            print("Subscribing email : {}".format(email))
            response = sns.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email)
            subscription_arn = response["SubscriptionArn"]

            timeout = 0
            while subscription_arn == 'pending confirmation':
                if timeout == max_timeout:
                    raise ValueError("Email is not confirmed : {}. subscription_arn : {}".format(email, subscription_arn))
                else:
                    print("Email {} has not been confirmed. subscription_arn : {}. Sleeping...".format(email, subscription_arn))
                    time.sleep(sleep_time)
                    timeout = timeout + 1
                    subscription_arn = [x['SubscriptionArn'] for x in sns.list_subscriptions()['Subscriptions'] if x['Endpoint'] == email][0]

            print("email {} subscription_arn has been confirmed : {}".format(email, subscription_arn))

            subject = "Message from DiningConcierge"
            message_body = """Hello! Here are my {cuisine} restaurant suggestions for {people_number} people, for {date} at {booking_time}: 1. {name0}, located at {location0}, 2. {name1}, located at {location1}, 3. {name2}, located at {location2}. Enjoy your meal!""".format(
                cuisine= cuisine,
                people_number= people_number,
                date= date,
                booking_time= booking_time,
                name0= names[0],
                location0= locations[0],
                name1= names[1],
                location1= locations[1],
                name2= names[2],
                location2= locations[2]
            )

            message_id = sns.publish(TopicArn=topic_arn, 
                    Message=message_body, 
                    Subject=subject)['MessageId']
            print("Message has been sent to {}".format(email))
            message.delete()
            print("Message has been deleted from SQS")

            return {
                'cuisine' : cuisine,
                'date' : date,
                'email' : email,
                'people_number' : people_number,
                'booking_time' : booking_time,
                'restaurant_ids': restaurant_ids,
                'names': names,
                'locations': locations,
                'subject': subject,
                'message': message_body,
                'message_id': message_id
            }
    else:
        print("No messages found!")