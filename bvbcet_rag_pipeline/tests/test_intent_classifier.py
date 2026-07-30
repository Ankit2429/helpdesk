"""Unit tests for IntentClassifier."""

from conversation.intent_classifier import Intent, IntentClassifier


def test_intent_classifier_greetings():
    classifier = IntentClassifier()
    assert classifier.classify("Hello there!") == Intent.GREETING
    assert classifier.classify("Hi, good morning") == Intent.GREETING
    assert classifier.classify("Namaste") == Intent.GREETING


def test_intent_classifier_thanks():
    classifier = IntentClassifier()
    assert classifier.classify("Thank you so much!") == Intent.THANKS
    assert classifier.classify("Thanks for the help") == Intent.THANKS


def test_intent_classifier_goodbye():
    classifier = IntentClassifier()
    assert classifier.classify("Goodbye!") == Intent.GOODBYE
    assert classifier.classify("Bye, see you later") == Intent.GOODBYE


def test_intent_classifier_small_talk():
    classifier = IntentClassifier()
    assert classifier.classify("How are you?") == Intent.SMALL_TALK
    assert classifier.classify("Who are you?") == Intent.SMALL_TALK


def test_intent_classifier_question():
    classifier = IntentClassifier()
    assert classifier.classify("When do KCET admissions start?") == Intent.QUESTION
    assert classifier.classify("What is the fee for B.E. Computer Science?") == Intent.QUESTION


def test_canned_responses():
    classifier = IntentClassifier()
    assert "Welcome to KLE" in classifier.get_canned_response(Intent.GREETING)
    assert "welcome" in classifier.get_canned_response(Intent.THANKS).lower()
