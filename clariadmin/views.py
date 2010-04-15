# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, permission_required
from django.conf import settings
from django.views.generic import list_detail

from clariadmin.models import Host
from clariadmin.forms import *
from common.diggpaginator import DiggPaginator

@login_required
@permission_required("clariadmin.can_access_clariadmin")
def list_all(request, *args, **kw):
    """
    
    Liste tous les tickets sans aucun filtre
    """
    
    search_mapping={'ip': 'istartswith',
        'automate': 'icontains',
        'hostname': 'istartswith'}
    
    form = SearchHostForm(request.POST)
    form.is_valid()
    
    qs = Host.objects.all()
    
    # Form cleaned_data ?
    try:
        if form.cleaned_data:
            cd = form.cleaned_data
            for key, value in cd.items():
                if value:
                    try:
                        lookup = search_mapping[key]
                    except KeyError:
                        lookup = 'exact'
                    qs = qs.filter(**{"%s__%s"%(key,lookup):value})
    except AttributeError:
        pass

    columns = [""]
    qs = qs.order_by(request.GET.get('sort', '-id'))
    paginator = DiggPaginator(qs, settings.TICKETS_PER_PAGE, body=5, tail=2, padding=2)
    page = paginator.page(request.GET.get("page", 1))

    return render_to_response("clariadmin/list.html", {
        "page": page,
        "form": form,
    }, context_instance=RequestContext(request))

@login_required
@permission_required("clariadmin.can_access_clariadmin")
def new(request):
    """
    Create a new host.
    """
    
    form = HostForm(request.POST)
    if request.POST:
        if form.is_valid():
            host = form.save()
            return redirect(host.get_absolute_url())
    return render_to_response('clariadmin/host.html', {'form': form }, context_instance=RequestContext(request))

@login_required
@permission_required("clariadmin.can_access_clariadmin")
def modify(request, host_id):
    host = get_object_or_404(Host, pk=host_id)
    if not request.POST:
        form = HostForm(instance=host)
    else:
        form = HostForm(request.POST, instance=host)
    
    if request.POST:
        if form.is_valid():
            form.save()
    return render_to_response("clariadmin/host.html", {"form": form, "host": host}, context_instance=RequestContext(request))

