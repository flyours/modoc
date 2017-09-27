# -*- coding: utf-8 -*-
import sys, os, logging
import datetime
import getopt
import re
import json
from collections import OrderedDict

reload(sys)
sys.setdefaultencoding("utf-8")

def initLog(level=logging.DEBUG):
    FORMAT = '[%(asctime)s ] %(levelname)s {%(pathname)s:%(lineno)d }: %(message)s'
    workDir = "/tmp/logs"
    if not os.path.exists(workDir):
        os.mkdir(workDir)

    #generatetime = datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
    #logFile = 'contract-doc' + str(generatetime) + ".log"
    logFile = "contract-doc.log"
    print "Log file Path:" + workDir + os.sep + logFile
    logging.basicConfig(filename=workDir + os.sep + logFile, format=FORMAT)
    logging.getLogger().setLevel(level)


def Usage():
    print "Usage: " + sys.argv[0] + " need parameter:"
    print "    -f | --config: configuration file"
    print "Example: python " + sys.argv[0] + " -f config.json"
    sys.exit(1)


class Common(object):
    def loadJson(self,fileName):
        try:
            return json.load(open(fileName))
        except Exception, e:
            print e.message
            print "Can not load Json:"+fileName
            logging.error(e.message)
            logging.error("Can not load Json:"+fileName)
            sys.exit(2)

    def validJson(self,jsonFile):
        if jsonFile.endswith(".json"):
            self.loadJson(jsonFile)

class ContractAPI(Common):
    def __init__(self, fileRoot, context, requestJson):
        self.fileRoot=fileRoot
        self.requestJson = requestJson
        self.context=context
        self.request=requestJson["request"]
        self.uri=self.request["uri"]
        self.method=self.request.get("method","get")
        self.url=self.context+self.uri
        logging.debug("handling url: %s ; method: %s"%(self.url,self.method))
        defaultDesc =self.method + self.url.replace("/", "_")
        self.description=requestJson.get("description", defaultDesc)
        self.requestFileName=""
        self.requestFileContent=""
        self.requestBody=self.genRequestBody()

        self.responseFileName=""
        self.responseFileContent=""
        self.response=requestJson["response"]
        self.responseBody=self.genResponseBody()

    def handleFile(self,jsonBody):
        if "file" in jsonBody:
            fileJson = jsonBody["file"]
            fullFileName=""
            fileName=""
            if type(fileJson) is unicode:
                fullFileName="%s/%s"%(self.fileRoot, fileJson)
                fileName=fileJson
            elif "json" in fileJson:
                fullFileName="%s/%s"%(self.fileRoot, fileJson["json"])
                fileName=fileJson["json"]
            elif "xml" in fileJson:
                fullFileName="%s/%s"%(self.fileRoot, fileJson["xml"])
                fileName=fileJson["xml"]

            content=""
            if os.path.exists(fullFileName):
                self.validJson(fullFileName)
                with open(fullFileName, 'r') as content_file:
                    content = content_file.read()
            else:
                logging.warn("file: %s not exist!"%fullFileName)

            return (fileName,content)

        return ("","")

    def genRequestBody(self):
        fileName,content=self.handleFile(self.request)
        if fileName:
            self.requestFileName=fileName
            self.requestFileContent=content
        return json.dumps(self.request, indent=2)

    def genResponseBody(self):
        fileName,content=self.handleFile(self.response)
        if fileName:
            self.responseFileName=fileName
            self.responseFileContent=content
        return json.dumps(self.response, indent=2)



class ApiConfig(Common):

    def __init__(self, confFile,outputFile):
        self.groups=self.loadJson(confFile)
        self.orderApiHash=OrderedDict()
        self.genApis()
        self.initTemplate()
        self.output(outputFile)

    def genApis(self):
        contextSet=set()
        descSet=set()
        for group in self.groups:
            fileRoot=group["file_root"]
            logging.debug("handling group: %s"%fileRoot)
            context=group.get("context","")
            include=group["include"]
            self.validItem("context",context,contextSet)
            apiHash=OrderedDict()
            for apiJson in self.loadJson("%s/%s"%(fileRoot,include)):
                api = ContractAPI(fileRoot, context, apiJson)
                self.validItem("description", api.description,descSet)
                if api.url in apiHash:
                    apiHash[api.url].append(api)
                else:
                    apiHash[api.url]=[api]
            self.orderApiHash[context]=apiHash

    def toId(self,path):
        path=re.sub(r"/","__",path)
        path=re.sub(r"\s","_",path)
        path=re.sub(r"\W","_",path)
        return path.lstrip("__")

    def output(self,outputHtml):
        outputFile = file(outputHtml, 'w')
        outputFile.write(self.docHead%"/api/ecommerce")
        for context, apiHash in self.orderApiHash.iteritems():
            outputFile.write(self.docPanelHead%(self.toId(context),context))
            for url,apiList in apiHash.iteritems():
                outputFile.write(self.docOneApiHead%(self.toId(url),
                                                     context,
                                                     url.replace(context,""),
                                                     self.toId(url)))
                for oneApi in apiList:
                    outputFile.write(self.docOneApiMethod%(self.toId(oneApi.description),
                                                     oneApi.method,
                                                     oneApi.method,
                                                     oneApi.description
                                                     ))
                outputFile.write(self.docOneApi)
                for oneApi in apiList:
                    modelId = self.toId(oneApi.description)
                    outputFile.write(self.docModal%(modelId,
                                                    oneApi.method,
                                                    oneApi.method,
                                                    context,
                                                    url.replace(context,""),
                                                    oneApi.description,
                                                    modelId+"_request",
                                                    modelId+"_response",
                                                    modelId+"_request",
                                                    oneApi.requestBody,
                                                    self.showFileContent(oneApi.requestFileName,oneApi.requestFileContent),
                                                    modelId+"_response",
                                                    oneApi.responseBody,
                                                    self.showFileContent(oneApi.responseFileName,oneApi.responseFileContent)
                                                    ))
                outputFile.write(self.docOneApiEnd)
            outputFile.write(self.docPanelEnd)
        outputFile.write(self.docListHead)
        for context, apiHash in self.orderApiHash.iteritems():
            outputFile.write(self.docListItem%(self.toId(context),context))
        outputFile.write(self.docEnd)

    def showFileContent(self,fileName,fileContent):
        if fileName:
            if fileName.endswith(".xml"):
                return '''fileName: %s<textarea style="width:100%%;height:300px;" readonly="true">%s</textarea>'''%(fileName,fileContent)
            return '''fileName: %s<pre><code>%s</code></pre>'''%(fileName,fileContent)
        return ""

    def validItem(self,itemName,item,itemSet):
        if item in itemSet:
            print "Error! %s : %s already exists"%(itemName,item)
            sys.exit(1)

        itemSet.add(item)


    def initTemplate(self):
        self.docHead='''\
<!DOCTYPE HTML>
<html>
<head><title>ECommerce contract server documentation</title>
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <meta name="generator" content="https://github.com/raml2html/raml2html 3.0.1">
    <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.1.1/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.3.0/styles/default.min.css">
    <script type="text/javascript" src="https://code.jquery.com/jquery-1.11.0.min.js"></script>
    <script type="text/javascript" src="https://netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min.js"></script>
    <script type="text/javascript"
            src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.3.0/highlight.min.js"></script>
    <script type="text/javascript">
        $(document).ready(function () {
            $('.page-header pre code, .top-resource-description pre code, .modal-body pre code').each(function (i, block) {
                hljs.highlightBlock(block);
            });

            $('[data-toggle]').click(function () {
                var selector = $(this).data('target') + ' pre code';
                $(selector).each(function (i, block) {
                    hljs.highlightBlock(block);
                });
            });

            // open modal on hashes like #_action_get
            $(window).bind('hashchange', function (e) {
                var anchor_id = document.location.hash.substr(1); //strip #
                var element = $('#' + anchor_id);

                // do we have such element + is it a modal?  --> show it
                if (element.length && element.hasClass('modal')) {
                    element.modal('show');
                }
            });

            // execute hashchange on first page load
            $(window).trigger('hashchange');

            // remove url fragment on modal hide
            $('.modal').on('hidden.bs.modal', function () {
                try {
                    if (history && history.replaceState) {
                        history.replaceState({}, '', '#');
                    }
                } catch (e) {
                }
            });
        });
    </script>
    <style>
        .hljs {
            background: transparent;
        }

        .parent {
            color: #999;
        }

        .list-group-item > .badge {
            float: none;
            margin-right: 6px;
        }

        .panel-title > .methods {
            float: right;
        }

        .badge {
            border-radius: 0;
            text-transform: uppercase;
            width: 70px;
            font-weight: normal;
            color: #f3f3f6;
            line-height: normal;
        }

        .badge_get {
            background-color: #63a8e2;
        }

        .badge_post {
            background-color: #6cbd7d;
        }

        .badge_put {
            background-color: #22bac4;
        }

        .badge_delete {
            background-color: #d26460;
        }

        .badge_patch {
            background-color: #ccc444;
        }

        .list-group, .panel-group {
            margin-bottom: 0;
        }

        .panel-group .panel + .panel-white {
            margin-top: 0;
        }

        .panel-group .panel-white {
            border-bottom: 1px solid #F5F5F5;
            border-radius: 0;
        }

        .panel-white:last-child {
            border-bottom-color: white;
            -webkit-box-shadow: none;
            box-shadow: none;
        }

        .panel-white .panel-heading {
            background: white;
        }

        .tab-pane ul {
            padding-left: 2em;
        }

        .tab-pane h1 {
            font-size: 1.3em;
        }

        .tab-pane h2 {
            font-size: 1.2em;
            padding-bottom: 4px;
            border-bottom: 1px solid #ddd;
        }

        .tab-pane h3 {
            font-size: 1.1em;
        }

        .tab-content {
            border-left: 1px solid #ddd;
            border-right: 1px solid #ddd;
            border-bottom: 1px solid #ddd;
            padding: 10px;
        }

        #sidebar {
            margin-top: 30px;
            padding-right: 5px;
            overflow: auto;
            height: 90%%;
        }

        .top-resource-description {
            border-bottom: 1px solid #ddd;
            background: #fcfcfc;
            padding: 15px 15px 0 15px;
            margin: -15px -15px 10px -15px;
        }

        .resource-description {
            border-bottom: 1px solid #fcfcfc;
            background: #fcfcfc;
            padding: 15px 15px 0 15px;
            margin: -15px -15px 10px -15px;
        }

        .resource-description p:last-child {
            margin: 0;
        }

        .list-group .badge {
            float: left;
        }

        .method_description {
            margin-left: 85px;
        }

        .method_description p:last-child {
            margin: 0;
        }

        .list-group-item {
            cursor: pointer;
        }

        .list-group-item:hover {
            background-color: #f5f5f5;
        }

        pre code {
            overflow: auto;
            word-wrap: normal;
            white-space: pre;
        }
    </style>
</head>
<body data-spy="scroll" data-target="#sidebar">
<div class="container">
    <div class="row">
        <div class="col-md-9" role="main">
            <div class="page-header"><h1>ECommerce Contract Server documentation</h1>
                <p>%s</p>
            </div>
        '''
        self.docPanelHead='''
            <div class="panel panel-default">
                <div class="panel-heading"><h3 id="%s" class="panel-title">%s</h3></div>
                <div class="panel-body">
                    <div class="panel-group">
        '''
        self.docOneApiHead='''
                        <div class="panel panel-white">
                            <div class="panel-heading">
                                <h4 class="panel-title">
                                    <a class="collapsed" data-toggle="collapse" href="#%s">
                                        <span class="parent">%s</span>%s
                                    </a>
                                </h4>
                            </div>
                            <div id="%s" class="panel-collapse collapse">
                                <div class="panel-body">
                                    <div class="list-group">
        '''
        self.docOneApiMethod='''
                                        <div onclick="window.location.href = '#%s'"
                                             class="list-group-item"><span class="badge badge_%s">%s</span>
                                            <div class="method_description"><p>%s</p></div>
                                            <div class="clearfix"></div>
                                        </div>
        '''
        self.docOneApi='''
                                    </div>
                                </div>
                            </div>
        '''
        self.docModal='''
                            <div class="modal fade" tabindex="0" id="%s">
                                <div class="modal-dialog">
                                    <div class="modal-content">
                                        <div class="modal-header">
                                            <button type="button" class="close" data-dismiss="modal" aria-hidden="true">
                                                &times;
                                            </button>
                                            <h4 class="modal-title"><span class="badge badge_%s">%s</span>
                                                <span class="parent">%s</span>%s</h4></div>
                                        <div class="modal-body">
                                            <div class="alert alert-info"><p>%s</p></div>
                                            <ul class="nav nav-tabs">
                                                <li class="active"><a href="#%s"
                                                                      data-toggle="tab">Request</a></li>
                                                <li><a href="#%s" data-toggle="tab">Response</a>
                                                </li>
                                            </ul>
                                            <div class="tab-content">
                                                <div class="tab-pane active" id="%s">
                                                    <pre><code>
%s
</code></pre>
%s
                                                </div>
                                                <div class="tab-pane" id="%s">
                                                    <pre><code>
%s
</code></pre>
%s
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
        '''
        self.docOneApiEnd='''
                        </div>
        '''
        self.docPanelEnd='''
                    </div>
                </div>
            </div>
        '''
        self.docListHead='''
        </div>
        <div class="col-md-3">
            <div id="sidebar" class="hidden-print affix" role="complementary">
                <ul class="nav nav-pills nav-stacked">
        '''
        self.docListItem='''
                    <li><a href="#%s">%s</a></li>
        '''
        self.docEnd='''
               </ul>
            </div>
        </div>
    </div>
</div>
</body>
</html>
        '''


if __name__ == '__main__':
    opts = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "f:")
    except getopt.GetoptError:
        Usage()

    configFile = ''
    for o, a in opts:
        if o in ('-f', '--config'):
            configFile = a
    if configFile == '':
        Usage()
    if not os.path.exists(configFile):
        print "Error: %s not exists, please check it!" % configFile
        sys.exit(2)
    dirname = os.path.dirname(configFile)
    if len(dirname) ==0: dirname="./"
    os.chdir(dirname)

    initLog()
    ApiConfig(configFile,"api-doc.html")
