import decimal
import ipaddress

from django.utils.text import capfirst
from django import forms
from django.db import models
from django_unixdatetimefield import UnixDateTimeField
from django_mysql.models import EnumField
from django.core import exceptions

from apps.accounts.models import Hostingprovider
from .choices import (
    ActionChoice,
    GreenlistChoice,
    CheckedOptions,
    BoolChoice,
    StatusApproval,
)

"""
- greencheck_linked - the purpose of the table is not very clear. Contains many entries though.
- greencheck_stats_total and greencheck_stats - self explanatory. Contained in this view here: https://admin.thegreenwebfoundation.org/admin/stats/greencheck

# wait for reply on these.
- greenenergy - also an old table
"""


class IpAddressField(models.DecimalField):
    default_error_messages = {
        'invalid': "'%(value)s' value must be a valid IpAddress.",
    }
    description = "IpAddress"

    def __init__(self, *args, **kwargs):
        kwargs.pop('max_digits', None)
        kwargs.pop('decimal_places', None)
        self.max_digits = 39
        self.decimal_places = 0
        super().__init__(
            *args, **kwargs,
            max_digits=self.max_digits, decimal_places=self.decimal_places
        )
        self.validators = []

    def to_python(self, value):
        if value is None:
            return value
        try:
            if hasattr(value, 'quantize'):
                return ipaddress.ip_address(int(value))
            return ipaddress.ip_address(value)
        except (TypeError, ValueError):
            raise exceptions.ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'value': value},
            )

    def get_db_prep_save(self, value, connection):
        value = self.get_prep_value(value)
        return connection.ops.adapt_decimalfield_value(value, self.max_digits, self.decimal_places)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return str(ipaddress.ip_address(int(value)))

    def get_prep_value(self, value):
        if value is not None:
            if isinstance(value, str):
                value = ipaddress.ip_address(value)

            return decimal.Decimal(int(value))
        return None

    def formfield(self, form_class=None, choices_form_class=None, **kwargs):
        """Return a django.forms.Field instance for this field."""
        defaults = {
            'required': not self.blank,
            'label': capfirst(self.verbose_name),
            'help_text': self.help_text,
        }
        if self.has_default():
            if callable(self.default):
                defaults['initial'] = self.default
                defaults['show_hidden_initial'] = True
            else:
                defaults['initial'] = self.get_default()
        defaults.update(kwargs)
        if form_class is None:
            form_class = forms.CharField
        return form_class(**defaults)


class GreencheckIp(models.Model):
    active = models.BooleanField(null=True)
    ip_end = IpAddressField(db_column='ip_eind')
    ip_start = IpAddressField()
    hostingprovider = models.ForeignKey(
        Hostingprovider, db_column='id_hp', on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.ip_start} - {self.ip_end}'

    class Meta:
        # managed = False
        db_table = 'greencheck_ip'
        indexes = [
            models.Index(fields=['ip_end'], name='ip_eind'),
            models.Index(fields=['ip_start'], name='ip_start'),
            models.Index(fields=['active'], name='active'),
        ]


class Greencheck(models.Model):
    hostingprovider = models.ForeignKey(
        Hostingprovider, db_column='id_hp', on_delete=models.CASCADE
    )
    greencheck_ip = models.ForeignKey(
        GreencheckIp, on_delete=models.CASCADE, db_column='id_greencheck'
    )
    date = UnixDateTimeField(db_column='datum')
    green = EnumField(choices=BoolChoice.choices)
    ip = IpAddressField()
    tld = models.CharField(max_length=64)
    type = EnumField(choices=GreenlistChoice.choices)
    url = models.CharField(max_length=255)

    class Meta:
        db_table = 'greencheck'

    def __str__(self):
        return f'{self.url} - {self.ip}'


class GreencheckIpApprove(models.Model):
    action = models.TextField(choices=ActionChoice.choices)
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE,
        db_column='id_hp', null=True
    )
    greencheck_ip = models.ForeignKey(
        GreencheckIp, on_delete=models.CASCADE, db_column='idorig', null=True
    )
    ip_end = IpAddressField(db_column='ip_eind')
    ip_start = IpAddressField()
    status = models.TextField(choices=StatusApproval.choices)

    def __str__(self):
        return f'{self.ip_start} - {self.ip_end}: {self.status}'

    class Meta:
        db_table = 'greencheck_ip_approve'
        # managed = False


class GreencheckLinked(models.Model):
    # waiting for use case first...
    pass


class GreenList(models.Model):
    greencheck = models.ForeignKey(
        Greencheck, on_delete=models.CASCADE, db_column='id_greencheck'
    )
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, db_column='id_hp'
    )
    last_checked = UnixDateTimeField()
    name = models.CharField(max_length=255, db_column='naam')
    type = EnumField(choices=GreenlistChoice.choices)
    url = models.CharField(max_length=255)
    website = models.CharField(max_length=255)

    class Meta:
        # managed = False
        db_table = 'greenlist'
        indexes = [
            models.Index(fields=['url'], name='url'),
        ]


class GreencheckTLD(models.Model):
    checked_domains = models.IntegerField()
    green_domains = models.IntegerField()
    hps = models.IntegerField(verbose_name='Hostingproviders registered in tld')
    tld = models.CharField(max_length=50)
    toplevel = models.CharField(max_length=64)

    class Meta:
        db_table = 'greencheck_tld'
        indexes = [
            models.Index(fields=['tld'], name='tld'),
        ]


class GreencheckASN(models.Model):
    active = models.BooleanField(null=True)
    # https://en.wikipedia.org/wiki/Autonomous_system_(Internet)
    asn = models.IntegerField(verbose_name='Autonomous system number')
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, db_column='id_hp'
    )

    class Meta:
        db_table = 'greencheck_as'
        indexes = [
            models.Index(fields=['active'], name='active'),
            models.Index(fields=['asn'], name='asn'),
        ]


class GreencheckASNapprove(models.Model):
    action = models.TextField(choices=ActionChoice.choices)
    asn = models.IntegerField()
    hostingprovider = models.ForeignKey(
        Hostingprovider, on_delete=models.CASCADE, db_column='id_hp'
    )
    greencheck_asn = models.ForeignKey(
        GreencheckASN, on_delete=models.CASCADE, db_column='idorig', null=True
    )
    status = models.TextField(choices=StatusApproval.choices)

    class Meta:
        db_table = 'greencheck_as_approve'

    def __str__(self):
        return f'Status: {self.status} Action: {self.action}'


# class Tld(models.Model):
#     # wait for confirmation
#     pass


# class MaxmindAsn(models.Model):
#     # wait for confirmation
#     pass


# STATS and stuff


class Stats(models.Model):
    checked_through = EnumField(choices=CheckedOptions.choices)
    count = models.IntegerField()
    ips = models.IntegerField()

    class Meta:
        abstract = True


class GreencheckStats(Stats):

    class Meta:
        # managed = False
        db_table = 'greencheck_stats'
        indexes = [
            models.Index(fields=['checked_through'], name='checked_through'),
        ]


class GreencheckStatsTotal(Stats):

    class Meta:
        # managed = False
        db_table = 'greencheck_stats_total'
        indexes = [
            models.Index(fields=['checked_through'], name='checked_through'),
        ]


class GreencheckWeeklyStats(models.Model):
    checks_green = models.IntegerField()
    checks_grey = models.IntegerField()
    checks_perc = models.FloatField()
    checks_total = models.IntegerField()

    monday = models.DateField(db_column='maandag')
    url_green = models.IntegerField()
    url_grey = models.IntegerField()
    url_perc = models.FloatField()
    week = models.IntegerField()
    year = models.PositiveSmallIntegerField()

    class Meta:
        # managed = False
        db_table = 'greencheck_weekly'
