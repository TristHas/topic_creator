#!/usr/bin/env python
# coding: utf-8

import os
import shutil
import random
import sys
import zipfile


#Comments
    # Question to David: What characters exactly are processed?
    # Topic names, anything interesting?
    # Considered extensions:
    # Proposal, concepts, what kind of syntax elements?
    # Comme pour corpus intégrer fonctions. Selon le type de fonction possible les associer aux inputs, aux outputs, etc.

# Conf
SENTENCE_LENGTH = 3
NUMBER_ENTRY_PER_TOPIC = 50


# Static
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
CORPUS_DIR = os.path.join(DATA_DIR,"corpus")
TEMPLATE_DIR = os.path.join(DATA_DIR,"templates")
TEMP_DIR = os.path.join(DATA_DIR,"tmp")
APP_DIR =os.path.join(DATA_DIR,"apps")
CORPUS_FILE_NAME = "corpus"
LANGUAGES = ["jpj", "frf", "enu"]
MANIFEST_LANG_NAME = {
        "jpj" : "ja_JP",
        "frf" : "fr_FR",
        "enu" : "en_US"
    }

class AppGenerator(object):
    def __init__(self):
        self.topic_gen={}
        self.supported_langs = LANGUAGES
        for l in self.supported_langs:
            self.topic_gen[l]=TopicGenerator(l)
        # init temp directory

    def __enter__(self):
        if os.path.isdir(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR, 0777)
        return self

    def __exit__(self, type, value, traceback):
        ##shutil.rmtree(TEMP_DIR)
        pass

    def make_app(self, uuid, langs, n_topics):
        for l in langs:
            assert l in self.supported_langs
        directory = os.path.join(TEMP_DIR, uuid)
        if os.path.isdir(directory):
            shutil.rmtree(directory)
        os.makedirs(directory, 0777)
        topic_infos = self._make_topic_info(n_topics)
        self._save_top_files(directory, topic_infos, langs)
        self._save_manifest(directory, uuid, topic_infos, langs)
        self._package_app(directory, uuid)

    def _package_app(self, directory, uuid):
        def zipdir(path, ziph):
            print path
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = os.path.join(root, file)
                    ziph.write(file_path, os.path.basename(file_path))

        filepath = os.path.join(APP_DIR, "".join([uuid, ".pkg"]))
        zipf = zipfile.ZipFile(filepath, 'w')
        zipdir(directory, zipf)
        zipf.close()




    def _save_manifest(self, directory, uuid, topic_infos, langs):
        line = self._manifest_header(uuid, langs) + self._manifest_content(topic_infos, langs) +self._manifest_tail()
        manifest = "\n".join(line)
        filename = os.path.join(directory,"manifest.xml")
        with open(filename, "w") as f:
            f.write(manifest)

    def _manifest_header(self, uuid, langs):
        line =[ "<?xml version='1.0' encoding='UTF-8'?>",
                 "<package version=\"0.0.8\" uuid=\"{}\">".format(uuid),
                 "   <names>",
                 "      <name lang=\"en_US\">{}</name>".format(uuid),
                 "   </names>",
                 "   <descriptions>",
                 "       <description lang=\"en_US\">test app for dialog</description>",
                 "   </descriptions>",
                 "   <descriptionLanguages>",
                 "       <language>en_US</language>",
                 "   </descriptionLanguages>",
                 "   <supportedLanguages>"
              ]
        #for l in langs:
        #    line.append("  <name lang=\"{}\">{}</name>".format(MANIFEST_LANG_NAME[l],uuid)
        for l in langs: # replace by langs
            line.append("      <language>{}</language>".format(MANIFEST_LANG_NAME[l]))
        line.append("   </supportedLanguages>")
        return line

    def _manifest_tail(self):
        line = ["   <requirements>",
                "      <naoqiRequirement minVersion=\"2.2\"/>",
                "      <robotRequirement model=\"JULIETTE\"/>",
                "      <robotRequirement model=\"NAO\"/>",
                "   </requirements>",
                "</package>"
                ]
        return line

    def _manifest_content(self,topic_infos, langs):
        line = ["   <contents>"]
        for topic_name in topic_infos.keys():
            x = ["      <dialogContent topicName=\"{}\" typeVersion=\"1.0\">".format(topic_name)]
            for l in langs:
                x.append("         <topic path=\"{}_{}.top\" language=\"{}\"/>".format(topic_name,l,MANIFEST_LANG_NAME[l]))
            x.append("      </dialogContent>")
            line.extend(x)
        line.append("   </contents>")
        return line

    def _save_top_files(self,directory, topic_infos, langs):
        for name in topic_infos.keys():
            for l in langs:
                filename = "".join([name,"_",l,".top"])
                filename = os.path.join(directory,filename)
                with open(filename,"w") as f:
                    f.write(self.topic_gen[l].make_topic(name, topic_infos[name]['n_entries'], topic_infos[name]['type']))
            if len(langs) > 1:
                # create .dlg
                pass

    def _make_topic_info(self, i):
        names = range(i)
        infos = {}
        for name in names:
            infos[str(name)] = {
                'type':random.random() / 4,
                'n_entries': NUMBER_ENTRY_PER_TOPIC
            }
        return infos




class TopicGenerator(object):
    def __init__(self, lang):
        self.lang = lang
        self.qichat = QiChatGenerator(lang)
        self.line = []

    def make_topic(self, name, n_entries, topic_type = 0.2):
        self._make_header(name)
        self._make_content(topic_type, n_entries)
        val = "".join(self.line)
        self.line = []
        return val

    #def _make_topic_name(self):        Names handled by app generator
    #    pass

    def _make_header(self, name):
        if self.line:
            sys.exit("Topic Generator has been asked to produce header on a non empty self.line")
        self.line.append("topic: ~{}() \n".format(name))
        self.line.append("language: {} \n".format(self.lang))
        self.line.append("\n")

    def _make_content(self, topic_type, n_entries):
        for i in range(n_entries):
            if random.random() > topic_type:
                self.line.append(self.qichat.make_rule())
            else:
                self.line.append(self.qichat.make_proposal())

class QiChatGenerator(object):
    def __init__(self, lang):
        self.corp = Corpus(lang)
        self.dic = self._refresh_dic()
        self._rule_templates = self._deserialize_rule_templates()
        self._proposal_templates = self._deserialize_proposal_templates()

    def make_rule(self):
        temp = self._get_rule_template()
        self._refresh_dic()
        rule = temp.format(**self.dic)
        rule = " ".join([rule, "\n"])
        return rule

    def make_proposal(self):
        temp = self._get_proposal_template()
        self._refresh_dic()
        proposal = temp.format(**self.dic)
        proposal = " ".join([proposal, "\n"])
        return proposal

    def make_concept(self):
        pass

    def _deserialize_rule_templates(self):
        filename = os.path.join(TEMPLATE_DIR,"qichat_rule_templates")
        temp = []
        with open(filename,'r') as f:
            for rule in f:
                temp.append(rule)
        return temp

    def _deserialize_proposal_templates(self):
        filename = os.path.join(TEMPLATE_DIR,"qichat_proposal_templates")
        temp = []
        with open(filename,'r') as f:
            for proposal in f:
                temp.append(proposal)
        return temp

    def _get_rule_template(self):
        return random.choice(self._rule_templates)

    def _get_proposal_template(self):
        return random.choice(self._proposal_templates)


    def _refresh_dic(self):
        self.dic = {
                'word1':self.corp.get_word(),
                'word2':self.corp.get_word(),
                'word3':self.corp.get_word(),
                'sentence1':self.corp.get_sentence(SENTENCE_LENGTH),
                'sentence2':self.corp.get_sentence(SENTENCE_LENGTH)
            }


class Corpus(object):
    def __init__(self, lang):
        self.words =self._deserialize_words_list(lang)
        self.card = len(self.words)
        self.lang = lang
        if self.lang == "jpj":
            self.sep = ""
            self.end = [""]
        else:
            self.sep = " "
            self.end = [""]

    def get_word(self):
        return random.choice(self.words)

    def _get_end(self):
        return random.choice(self.end)

    def get_sentence(self, n_words):
        sentence = self.sep.join(random.sample(self.words, n_words))
        return "".join([sentence, self._get_end()])

    def _deserialize_words_list(self, lang = "jpj"):
        filename = os.path.join(CORPUS_DIR, ".".join([CORPUS_FILE_NAME, lang]))
        corpus = []
        with open(filename, "r") as f:
            for x in f:
                x = x.strip()
                corpus.append(x)
        return corpus



if __name__ == "__main__":
    with AppGenerator() as app:
        app.make_app("test_app",["jpj", "frf", "enu"], 100)








# Topic generator init creates a temporary dirAppGenerator
if __name__ == "__mainnn__":
    def useless_corpus_copy():
        filename = "/Users/d-fr-mac0002/Desktop/dialog/topic_generator/data/corpus/liste_mots.txt"
        with open(filename, "r") as f:
            with open("/Users/d-fr-mac0002/Desktop/dialog/topic_generator/data/corpus/corpus.frf", "w") as f_write:
                i = 0
                for line in f:
                    i +=1
                    word = line.split()[1]
                    print word
                    f_write.write(word)
                    f_write.write("\n")
        print i

    useless_corpus_copy()

