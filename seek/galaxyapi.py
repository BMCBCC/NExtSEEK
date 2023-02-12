#!/usr/bin/env python
from datetime import datetime, timedelta
import subprocess
import json
from subprocess import call

class GalaxyAPI(object):
    def __init__(self, url, email, password):
        self.__url = url
        self.__email = email
        self.__password = password
        self.__gi = GalaxyInstance(
            url=url,
            email=email,
            password=password)
            

    def get_galaxy_info(self):
        gusername = ""
        user = self.__gi.users.get_current_user()
        gusername = user['username']
        workflows = self.__gi.workflows.get_workflows
        history = self.__gi.histories.get_histories()
        hist = json.dumps(history)
        his = json.loads(hist)
        genomes = self.__gi.genomes.get_genomes()
        dbkeys = []
        ftp = self.__gi.config.get_config()["ftp_upload_site"]
        if "bioinf-galaxian" in ftp:
            ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
        for gene in genomes:
            for g in gene:
                if "(" not in g:
                    dbkeys.append(g)
        return gusername, workflows, his, dbkeys


    def get_history_id(self):
        cur_hist = self.__gi.histories.get_current_history()
        current = json.dumps(cur_hist)
        current_hist = json.loads(current)
        history_id = current_hist['id']
        return history_id


    def get_input_data(self):
        history_id = self.get_history_id()
        hist_contents = self.__gi.histories.show_history(history_id, contents=True)
        inputs = {}
        datacount = 0
        datasets = [dataset for dataset in hist_contents if not dataset['deleted']]
        for dataset in datasets:
            inputs[dataset['name']] = dataset['id']
            datacount += 1
        return inputs, datacount
    
    def create_new_hist(self, workflowid, files, new_hist):
        date = format(datetime.now() + timedelta(hours=2))
        if workflowid != "0":
            if len(list(filter(None, files))) >= 0:
                workflow = self.__gi.workflows.show_workflow(workflowid)
                if new_hist is None or new_hist == "":
                    new_hist_name = (workflow['name'] + "_" + date)
                else:
                    new_hist_name = new_hist
                self.__gi.histories.create_history(name=new_hist_name)
                history_id = self.get_history_id()
            else:
                pass
        else:
            if len(list(filter(None, files))) >= 0:
                if new_hist is None or new_hist == "":
                    new_hist_name = ("Use_Galaxy_" + date)
                else:
                    new_hist_name = new_hist
                self.__gi.histories.create_history(name=new_hist_name)
                history_id = self.get_history_id()
            else:
                pass
        return history_id
    
    def get_output(self):
        historyid = self.get_history_id()
        inputs = []
        input_ids = []
        outputs = []
        time.sleep(30)
        hist = self.__gi.histories.show_history(historyid)
        state = hist['state_ids']
        dump = json.dumps(state)
        status = json.loads(dump)
        while (
            status['running'] or
            status['queued'] or
            status['new'] or
            status['upload']
        ):
            time.sleep(90)
            hist = self.__gi.histories.show_history(historyid)
            state = hist['state_ids']
            dump = json.dumps(state)
            status = json.loads(dump)
            if (
                    not status['running'] and
                    not status['queued'] and
                    not status['new'] and
                    not status['upload']
            ):
                break
        files = status['ok']
        for o in files:
            oug = self.__gi.datasets.show_dataset(o, deleted=False, hda_ldda='hda')
            if "input_" in oug['name']:
                inputs.append(oug['id'])
            else:
                outputs.append(oug)
        for i in inputs:
            iug = self.__gi.datasets.show_dataset(i, deleted=False, hda_ldda='hda')
            input_ids.append(iug)
        in_url = []
        in_name = []
        out_url = []
        out_name = []
        for input_id in input_ids:
            in_name.append(input_id["name"])
            in_url.append(input_id["download_url"])
        for out in outputs:
            if out['visible']:
                out_name.append(out["name"])
                out_url.append(out["download_url"])
        return in_url, in_name, out_url, out_name
    
    def create_history(self, resultid):
        ftp = self.__gi.config.get_config()["ftp_upload_site"]
        if "bioinf-galaxian" in ftp:
            ftp = "ftp://bioinf-galaxian.erasmusmc.nl:23"
        self.__gi.histories.create_history(name=resultid)
        return ftp
    
    def rerun_owncloud_workflow(self, gafile, history_id):
        self.__gi.workflows.import_workflow_from_local_path(gafile.name)
        workflows = self.__gi.workflows.get_workflows(name="TEMP_WORKFLOW")
        for workflow in workflows:
            newworkflowid = workflow["id"]
        datamap = dict()
        mydict = {}
        jsonwf = self.__gi.workflows.export_workflow_json(newworkflowid)
        for i in range(len(jsonwf["steps"])):
            if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                try:
                    label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                except IndexError:
                    label = jsonwf["steps"][str(i)]["label"]
                mydict[label] = self.__gi.workflows.get_workflow_inputs(
                    newworkflowid, label=label)[0]
        for k, v in mydict.items():
            datasets = self.get_input_data()[0]
            for dname, did in datasets.items():
                if k in dname:
                    datamap[v] = {'src': "hda", 'id': did}
        self.__gi.workflows.run_workflow(
            newworkflowid,
            datamap,
            history_id=history_id
        )
        self.__gi.workflows.delete_workflow(newworkflowid)
        
    
    
    def rerun_seek_workflow(self, username, workflowid, history_id, gacont):
        with open(username + "/workflow.ga", 'w') as gafile:
            json_ga = json.loads(gacont)
            for i, dummyj in json_ga.items():
                if i == 'name':
                    json_ga[i] = 'TEMP_WORKFLOW'
            json.dump(json_ga, gafile, indent=2)
        if workflowid != "0":
            self.__gi.workflows.import_workflow_from_local_path(gafile.name)
            workflows = self.__gi.workflows.get_workflows(name="TEMP_WORKFLOW")
            for workflow in workflows:
                newworkflowid = workflow["id"]
            datamap = dict()
            mydict = {}
            jsonwf = self.__gi.workflows.export_workflow_json(newworkflowid)
            for i in range(len(jsonwf["steps"])):
                if jsonwf["steps"][str(i)]["name"] == "Input dataset":
                    try:
                        label = jsonwf["steps"][str(i)]["inputs"][0]["name"]
                    except IndexError:
                        label = jsonwf["steps"][str(i)]["label"]
                    mydict[label] = self.__gi.workflows.get_workflow_inputs(
                        newworkflowid, label=label)[0]
            for k, v in mydict.items():
                datasets = self.get_input_data()[0]
                for dname, did in datasets.items():
                    if k in dname:
                        datamap[v] = {'src': "hda", 'id': did}
            self.__gi.workflows.run_workflow(
                newworkflowid, datamap, history_id=history_id)
            self.__gi.workflows.delete_workflow(newworkflowid)
            