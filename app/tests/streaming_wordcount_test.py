import logging
import unittest
import uuid
import os

import pytest
from hamcrest.core.core.allof import all_of

from app import streaming_wordcount
from apache_beam.io.gcp.tests.pubsub_matcher import PubSubMessageMatcher
from apache_beam.runners.runner import PipelineState
from apache_beam.testing import test_utils
from apache_beam.testing.pipeline_verifiers import PipelineStateMatcher
from apache_beam.testing.test_pipeline import TestPipeline


INPUT_TOPIC = 'wc_topic_input'
OUTPUT_TOPIC = 'wc_topic_output'
INPUT_SUB = 'wc_subscription_input'
OUTPUT_SUB = 'wc_subscription_output'

DEFAULT_INPUT_NUMBERS = 5
WAIT_UNTIL_FINISH_DURATION = 6 * 60 * 1000  # in milliseconds


class StreamingWordCountIT(unittest.TestCase):
    def setUp(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./app/keys/k8s_owner_key.json"
        self.test_pipeline = TestPipeline()
        self.uuid = str(uuid.uuid4())

        # Set up PubSub environment.
        from google.cloud import pubsub
        import google.auth
        self.credentials, self.project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        self.pub_client = pubsub.PublisherClient()
        self.input_topic = self.pub_client.create_topic(
            name=self.pub_client.topic_path(self.project, INPUT_TOPIC + self.uuid))
        self.output_topic = self.pub_client.create_topic(
            name=self.pub_client.topic_path(self.project, OUTPUT_TOPIC + self.uuid))

        self.sub_client = pubsub.SubscriberClient()
        self.input_sub = self.sub_client.create_subscription(
            name=self.sub_client.subscription_path(
                self.project, INPUT_SUB + self.uuid),
            topic=self.input_topic.name)
        self.output_sub = self.sub_client.create_subscription(
            name=self.sub_client.subscription_path(
                self.project, OUTPUT_SUB + self.uuid),
            topic=self.output_topic.name,
            ack_deadline_seconds=60)

    def _inject_numbers(self, topic, num_messages):
        """Inject numbers as test data to PubSub."""
        logging.debug(
            'Injecting %d numbers to topic %s',
            num_messages, topic.name)
        for n in range(num_messages):
            self.pub_client.publish(
                self.input_topic.name, str(n).encode('utf-8'))

    def tearDown(self):
        test_utils.cleanup_subscriptions(
            self.sub_client, [self.input_sub, self.output_sub])
        test_utils.cleanup_topics(
            self.pub_client, [self.input_topic, self.output_topic])

    @pytest.mark.it_postcommit
    def test_streaming_wordcount_it(self):
        # Build expected dataset.
        expected_msg = [('%d: 1' % num).encode('utf-8')
                        for num in range(DEFAULT_INPUT_NUMBERS)]

        # Set extra options to the pipeline for test purpose
        state_verifier = PipelineStateMatcher(PipelineState.RUNNING)
        pubsub_msg_verifier = PubSubMessageMatcher(
            self.project, self.output_sub.name, expected_msg, timeout=400)
        extra_opts = {
            'input_subscription': self.input_sub.name,
            'output_topic': self.output_topic.name,
            'wait_until_finish_duration': WAIT_UNTIL_FINISH_DURATION,
            'on_success_matcher': all_of(state_verifier, pubsub_msg_verifier)
        }

        # Generate input data and inject to PubSub.
        self._inject_numbers(self.input_topic, DEFAULT_INPUT_NUMBERS)

        # Get pipeline options from command argument: --test-pipeline-options,
        # and start pipeline job by calling pipeline main function.
        streaming_wordcount.run(
            self.test_pipeline.get_full_options_as_args(**extra_opts),
            save_main_session=False)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
