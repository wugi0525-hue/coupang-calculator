import sys
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
import test_prompt
