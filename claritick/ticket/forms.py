# -*- coding: utf-8 -*-

import datetime
from django import forms
from dojango import forms as df
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.sites.models import Site

from ticket.models import *
from common.widgets import *
from common.forms import ModelFormTableMixin
from common.models import ClaritickUser
from common.utils import filter_form_for_user, filter_ticket_for_user
from common.utils import sort_queryset
from common.widgets import FilteringSelect

from bondecommande.models import BonDeCommande


class BonDeCommandeModelChoiceField(df.ModelChoiceField):
    def label_from_instance(self, obj):
        return u"n°%s pour %s (le %s)" % (obj.id, obj.client, obj.date_creation.strftime("%Y/%m/%d"))


class CustomModelForm(forms.ModelForm):
    def get_exact_id(self):
        prefix = self.prefix + '-' if self.prefix else ''
        return self.auto_id % prefix + '%s'


class PartialNewTicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("category",)


class NewTicketForm(CustomModelForm):
    title = forms.CharField(label=u'Titre', widget=forms.TextInput(attrs={'size': '80'}))
    text = df.CharField(label=u'Texte', widget=forms.Textarea(attrs={'cols': '90', 'rows': '15'}))
    client = df.ModelChoiceField(queryset=Client.objects.all(),
                                 widget=FilteringSelect(attrs={'queryExpr': '${0}*', 'onChange': 'modif_ticket();'}),
                                 empty_label='', required=False)
    keywords = forms.CharField(label=u'Mots clefs',
                               widget=forms.TextInput(attrs={'size': '80'}),
                               required=False)
    calendar_start_time = df.DateTimeField(required=False)
    calendar_end_time = df.DateTimeField(required=False)
    assigned_to = df.ModelChoiceField(
        label=u'Assigné à',
        widget=FilteringSelect(attrs={'onChange': 'modif_ticket();'}),
        queryset=ClaritickUser.objects.all(),
        required=False)
    #validated_by = df.ModelChoiceField(widget=FilteringSelect(), queryset=ClaritickUser.objects.all(), required=False)
    file = df.FileField(label='Fichier joint', required=False)
    comment = df.CharField(widget=forms.Textarea(attrs={'cols': '80', 'style': 'margin:10px;'}),
                           required=False)
    internal = forms.BooleanField(widget=df.widgets.CheckboxInput(attrs={'onChange': 'modif_ticket(); toggleComment(this);'}),
                                  initial=True, required=False)
    appel = forms.BooleanField(label=u"Signaler un (r)appel du client",
                               widget=df.widgets.CheckboxInput(attrs={'onChange': 'modif_ticket();'}),
                               initial=False, required=False)
    delete_rappel = forms.BooleanField(label=u"Désactiver le rappel du ticket",
                                       widget=df.widgets.CheckboxInput(attrs={'onChange': 'modif_ticket();'}),
                                       initial=False, required=False)
    calendar_rappel = df.DateTimeField(required=False)
    bondecommande = BonDeCommandeModelChoiceField(
        label=u'Bon de commande',
        widget=FilteringSelect(attrs={'onChange': 'modif_ticket();', 'style': 'width:400px'}),
        queryset=BonDeCommande.objects.filter(ticket=None), required=False)

    class Meta:
        model = Ticket
        exclude = ("opened_by", "validated_by", "diffusion", "alarm", )

    def __init__(self, *args, **kwargs):
        # LC: Get the instance / Assigned to for permission workaround:
        # If a ticket is assigned to a user which the current modifying user
        # can't view/assign to, then display it anyway in order to keep it.
        instance = kwargs.get("instance", None)
        current_assigned_to = instance and instance.assigned_to or None
        filter_ticket_for_user(self, kwargs.pop("user", None), current_assigned_to)
        super(NewTicketForm, self).__init__(*args, **kwargs)

    def clean_keywords(self):
        keywords = self.cleaned_data['keywords']
        return ','.join([kw.strip() for kw in keywords.split(',')])

class NewTicketSmallForm(NewTicketForm):
    class Meta:
        model = Ticket
        exclude = ("opened_by", "category", "project", "keywords", "priority", "assigned_to", "validated_by", "diffusion", "alarm", )


class ChildFormSmall(CustomModelForm):
    title = df.CharField(label=u'Titre', widget=forms.TextInput(attrs={'size': '80'}), required=True)
    text = df.CharField(widget=forms.Textarea(attrs={'cols': '90', 'rows': '15'}))

    class Meta:
        model = Ticket
        fields = ("title", "text")


class ChildForm(ChildFormSmall):
    title = df.CharField(label=u'Titre',
                         widget=forms.TextInput(attrs={'size': '80', 'onBlur': 'showDeletebox(this);'}),
                         required=True)
    text = df.CharField(widget=forms.Textarea(attrs={'cols': '90', 'rows': '15', 'onBlur': 'showDeletebox(this);'}))
    keywords = df.CharField(widget=forms.TextInput(attrs={'size': '80'}),
                            required=False)
    state = forms.ModelChoiceField(label=u'État',
                                   queryset=State.objects.all())
    assigned_to = df.ModelChoiceField(widget=FilteringSelect(attrs={'onChange': 'modif_ticket();'}),
                                      label=u'Assigné à',
                                      queryset=ClaritickUser.objects.all(),
                                      required=False)
    project = forms.ModelChoiceField(label=u'Projet',
                                     queryset=Project.objects.all(),
                                     required=False)
    diffusion = forms.NullBooleanField(widget=forms.HiddenInput(),
                                       initial=False)
    comment = forms.CharField(widget=forms.Textarea(),
                              required=False)
    internal = forms.BooleanField(widget=df.widgets.CheckboxInput(attrs={'onChange': 'toggleComment(this)'}),
                                  initial=True, required=False)

    class Meta:
        model = Ticket
        fields = ("state", "title", "text", "keywords", "assigned_to",
                  "category", "project", "diffusion")

    def __init__(self, *args, **kwargs):
        filter_form_for_user(self, kwargs.pop("user", None))
        super(ChildForm, self).__init__(*args, **kwargs)


class SearchTicketForm(df.Form, ModelFormTableMixin):
    title = df.CharField(label=u'Titre',
                         widget=df.TextInput(attrs={'size': '64'}),
                         required=False)
    client = df.ChoiceField(choices=[(x.pk, x) for x in sort_queryset(Client.objects.all())],
                            widget=FilteringSelect(),
                            required=False)
    category = df.ModelChoiceField(label=u'Catégorie',
                                   queryset=Category.objects.all(),
                                   widget=FilteringSelect(),
                                   empty_label='', required=False)
    project = df.ModelChoiceField(label=u'Projet',
                                  queryset=Project.objects.all(),
                                  widget=FilteringSelect(),
                                  empty_label='', required=False)
    state = df.ModelChoiceField(label=u'État',
                                queryset=State.objects.all(),
                                widget=FilteringSelect(),
                                empty_label='', required=False)
    priority = df.ModelChoiceField(label=u'Priorité',
                                   queryset=Priority.objects.all(),
                                   widget=FilteringSelect(),
                                   empty_label='', required=False)
    assigned_to = df.ChoiceField(label=u'Assigné a',
                                 widget=FilteringSelect(),
                                 required=False)

    text = df.CharField(label=u'Texte', required=False)
    opened_by = df.ChoiceField(label=u'Ouvert part',
                               widget=FilteringSelect(),
                               required=False)
    keywords = df.CharField(label=u'Mots clefs', required=False)
    contact = df.CharField(required=False)

    def __init__(self, *args, **kwargs):
        filter_form_for_user(self, kwargs.pop("user", None))
        self.base_fields["opened_by"].choices = self.base_fields["assigned_to"].choices
        super(SearchTicketForm, self).__init__(*args, **kwargs)


class SearchTicketViewFormInverted(df.Form):
    not_client = df.MultipleChoiceField(
        label=u'Client',
        choices=[(x.pk, x) for x in sort_queryset(Client.objects.all())],
        required=False,
        widget=df.CheckboxSelectMultiple()
    )
    not_project = df.MultipleChoiceField(
        label=u'Projet',
        required=False,
        widget=df.CheckboxSelectMultiple()
    )
    not_category = df.MultipleChoiceField(
        label=u'Catégorie',
        required=False,
        widget=df.CheckboxSelectMultiple()
    )
    not_priority = df.MultipleChoiceField(
        label=u'Priorité',
        required=False,
        widget=df.CheckboxSelectMultiple()
    )
    not_state = df.MultipleChoiceField(
        label=u'État',
        required=False,
        widget=df.CheckboxSelectMultiple()
    )
    not_assigned_to = df.MultipleChoiceField(
        label=u'Assigné à',
        required=False,
        widget=df.CheckboxSelectMultiple()
    )

    def __init__(self, *args, **kwargs):
        self.base_fields["not_state"].choices = State.objects.values_list("pk", "label")
        self.base_fields["not_category"].choices = Category.objects.values_list("pk", "label")
        self.base_fields["not_project"].choices = Project.objects.values_list("pk", "label")
        self.base_fields["not_priority"].choices = Priority.objects.values_list("pk", "label")
        self.base_fields["not_assigned_to"].choices = User.objects.values_list("pk", "username")
        filter_form_for_user(self, kwargs.pop("user", None), keywords=("not_client", "not_assigned_to"))

        super(SearchTicketViewFormInverted, self).__init__(*args, **kwargs)
        # On retire les choix vide, provenant de SearchTicketForm
        del self.base_fields["not_assigned_to"].choices[0]
        del self.base_fields["not_client"].choices[0]


class SearchTicketViewForm(SearchTicketForm):
    client = df.ChoiceField(choices=[(x.pk, x) for x in sort_queryset(Client.objects.all())],
                            widget=FilteringSelect(),
                            required=False)
    view_name = df.CharField(widget=df.TextInput(),
                             label=u"Nom de la vue",
                             required=False)
    state = df.MultipleChoiceField(label=u'État',
                                   required=False,
                                   widget=df.CheckboxSelectMultiple())
    category = df.MultipleChoiceField(label=u'Catégorie',
                                      required=False,
                                      widget=df.CheckboxSelectMultiple())
    project = df.MultipleChoiceField(label=u'Projet',
                                     required=False,
                                     widget=df.CheckboxSelectMultiple())
    priority = df.MultipleChoiceField(label=u'Priorité',
                                      required=False,
                                      widget=df.CheckboxSelectMultiple())
    assigned_to = df.MultipleChoiceField(label=u'Assigné à',
                                         required=False,
                                         widget=df.widgets.CheckboxSelectMultiple())
    opened_by = df.MultipleChoiceField(label=u'Ouvert par',
                                       required=False,
                                       widget=df.widgets.CheckboxSelectMultiple())
    notseen = df.BooleanField(label=u"Non consultés",
                              widget=df.widgets.CheckboxInput(),
                              initial=False, required=False)
    title = df.CharField(label=u'Titre',
                         required=False,
                         widget=df.TextInput())
    text = df.CharField(label=u'Texte',
                        required=False,
                        widget=df.TextInput())
    keywords = df.CharField(label=u'Mots clefs',
                            required=False,
                            widget=df.TextInput())

    def __init__(self, *args, **kwargs):
        self.base_fields["state"].choices = State.objects.values_list("pk", "label")
        self.base_fields["category"].choices = Category.objects.values_list("pk", "label")
        self.base_fields["project"].choices = Project.objects.values_list("pk", "label")
        self.base_fields["priority"].choices = Priority.objects.values_list("pk", "label")

        filter_form_for_user(self, kwargs.pop("user", None))
        super(SearchTicketViewForm, self).__init__(*args, **kwargs)

        # On retire les choix vide, provenant de SearchTicketForm
        del self.base_fields["assigned_to"].choices[0]
        del self.base_fields["opened_by"].choices[0]

    def clean_view_name(self):
        name = self.cleaned_data["view_name"]
        if name == "" or name is None:
            return u"Nouvelle vue"
        return name


class TicketActionsForm(df.Form):
    actions = df.ChoiceField(widget=df.FilteringSelect(), required=False)
    assigned_to = df.ModelChoiceField(queryset=User.objects.all(),
        widget=FilteringSelect(attrs={"style": "display: none;"}),
        empty_label='', required=False)
    category = df.ModelChoiceField(queryset=Category.objects.all(),
        widget=FilteringSelect(attrs={"style": "display: none;"}),
        empty_label='', required=False)
    project = df.ModelChoiceField(queryset=Project.objects.all(),
        widget=FilteringSelect(attrs={"style": "display: none;"}),
        empty_label='', required=False)
    state = df.ModelChoiceField(queryset=State.objects.all(),
        widget=FilteringSelect(attrs={"style": "display: none;"}),
        empty_label='', required=False)
    priority = df.ModelChoiceField(queryset=Priority.objects.all(),
        widget=FilteringSelect(attrs={"style": "display: none;"}),
        empty_label='', required=False)
    comment = df.CharField(widget=df.HiddenInput(), required=False)

    model = Ticket.objects

    def __init__(self, *args, **kwargs):
        try:
            self.queryset = self.model.filter(id__in=args[0].getlist("ticket_checked"))
        except KeyError:
            self.queryset = self.model.none()

        self.base_fields["actions"].choices = self.get_actions()
        self.base_fields["actions"].choices.insert(0, ("", ""))

        filter_form_for_user(self, kwargs.pop("user", None))
        super(TicketActionsForm, self).__init__(*args, **kwargs)

    def get_actions(self):
        return [
            ("action_close_tickets", u"Fermer les tickets sélectionnés"),
            ("action_change_assigned_to", u"Modifier l'assignation"),
            ("action_change_category", u"Modifier la catégorie"),
            ("action_change_project", u"Modifier le projet"),
            ("action_change_state", u"Modifier l'état"),
            ("action_change_priority", u"Modifier la priorité"),
            ("action_validate_tickets", u"Valider les tickets sélectionnées"),
        ]

    def process_actions(self, request):
        if self.is_valid():
            action = self.cleaned_data["actions"]
            try:
                attr = getattr(self, action)
                attr(self.queryset, request)
                return True
            except AttributeError:
                return False
        return False

    def clean(self):
        cd = self.cleaned_data
        if cd["actions"] == "action_close_tickets" or (
                cd["actions"] == "action_change_state" and
                cd["state"] and
                cd["state"].pk == settings.TICKET_STATE_CLOSED):
            if not cd["comment"]:
                raise forms.ValidationError(u"Vous devez saisir un commentaire de clotûre pour le/les tickets sélectionné(s).")

        if cd["actions"] == "action_change_state" and not cd["state"]:
            raise forms.ValidationError(u"Vous devez choisir un état à appliquer.")
        if cd["actions"] == "action_change_assigned_to" and not cd["assigned_to"]:
            raise forms.ValidationError(u"Vous devez choisir une nouvelle assignation.")
        if cd["actions"] == "action_change_category" and not cd["category"]:
            raise forms.ValidationError(u"Vous devez choisir une nouvelle catégorie.")
        if cd["actions"] == "action_change_project" and not cd["project"]:
            raise forms.ValidationError(u"Vous devez choisir un nouveau project.")
        if cd["actions"] == "action_change_priority" and not cd["priority"]:
            raise forms.ValidationError(u"Vous devez choisir une nouvelle priorité.")

        return cd

    def action_close_tickets(self, qs, request):
        qs.update(state=settings.TICKET_STATE_CLOSED, date_close=datetime.datetime.now())
        for ticket in qs:
            Comment.objects.create(
                content_object=ticket,
                site=Site.objects.get_current(),
                user=request.user,
                user_name=request.user.username,
                user_email=request.user.email,
                comment=self.cleaned_data["comment"],
                submit_date=datetime.datetime.now(),
                is_public=True,
                is_removed=False
            )

    def action_change_assigned_to(self, qs, request):
        qs.update(assigned_to=self.cleaned_data["assigned_to"])

    def action_change_category(self, qs, request):
        qs.update(category=self.cleaned_data["category"])

    def action_change_project(self, qs, request):
        qs.update(project=self.cleaned_data["project"])

    def action_change_state(self, qs, request):
        if self.cleaned_data["state"].pk == settings.TICKET_STATE_CLOSED:
            self.action_close_tickets(qs, request)
        else:
            qs.update(state=self.cleaned_data["state"])

    def action_change_priority(self, qs, request):
        qs.update(priority=self.cleaned_data["priority"])

    def action_validate_tickets(self, qs, request):
        qs.update(validated_by=request.user)


class TicketActionsSmallForm(TicketActionsForm):
    def get_actions(self):
        return [
            ("action_close_tickets", u"Fermer les tickets sélectionnés"),
        ]

    def process_actions_(self):
        if self.is_valid():
            if self.cleaned_data["actions"] not in ("action_close_tickets"):
                return False
            return super(TicketActionsSmallForm, self).process_actions()
