# -*- coding: utf-8 -*-

from django import http
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import permission_required
from django.views.decorators.csrf import csrf_exempt
from common.decorator import render_to_json
from packaging.models import Package, PackageConfig, ClientPackageAuth
from django.db.models import Q
import os.path


@permission_required("package.can_access")
def list(request, *args, **kwargs):
    qs = Package.objects.all()
    qs = qs.order_by("name")
    context = { "packages": qs }
    return render_to_response('packaging/list.html',
                              context,
                              context_instance=RequestContext(request))

@csrf_exempt
@render_to_json(indent=2)
def listjson(request, *args, **kwargs):
    request.is_text_exception = True
    data = request.POST
    try:
        authkey = data["authkey"]
    except KeyError:
        return http.HttpResponse('No permission without valid key.', status=403)

    # First determine packageAuth client
    try:
        packageauth = ClientPackageAuth.objects.get(key=authkey)
    except ClientPackageAuth.DoesNotExist:
        return http.HttpResponse('invalid key.', status=403)

    dataDictList = []
    for p in Packages.objects.filter(clients__in=packageauth.client):
        dataDictList.append({
            "name": p.name,
            "platform": p.platform,
            # TODO
        })
    return dataDictList

@csrf_exempt
@render_to_json(indent=2)
def getconfig(request, *args, **kwargs):
    request.is_text_exception = True
    data = request.POST
    try:
        authkey = data["authkey"]
    except KeyError:
        return http.HttpResponse('No permission without valid key.', status=403)
    
    # Get packageAuth client
    try:
        packageauth = ClientPackageAuth.objects.get(key=authkey)
    except ClientPackageAuth.DoesNotExist:
        return http.HttpResponse('invalid key.', status=403)
    # Getting a list of possible configurations
    configs = PackageConfig.objects.filter(packageauth=packageauth)
    configDictList = []
    for config in configs:
        configDictList.append(config.todict())
    # And that's all folks
    return configDictList

@csrf_exempt
def download(request, package_id):
    package = get_object_or_404(Package, pk=package_id)
    file = package.file

    response = http.HttpResponse(content_type="application/octet-stream")
    response['Cache-Control'] = 'no-cache'
    response['Pragma'] = 'no-cache'
    response['Content-Transfer-Encoding'] = 'binary'
    try:
        response["Content-Disposition"] = "attachment; filename=\"%s\"" % file.name
    except UnicodeEncodeError:
        ext = file.filename.split(".")[-1]
        response["Content-Disposition"] = "attachment; filename=package%s.%s" % (file.id, ext)

    response["Content-Length"] = file.size
    for c in file.chunks(chunk_size=512 * 1024):  # 512kiB chunk
        response.write(c)
    response.flush()
    return response

@csrf_exempt
def autoupdate(request):
    print "autoupdate received %s" % (request.POST,)
    return http.HttpResponse('OK.', status=200)
