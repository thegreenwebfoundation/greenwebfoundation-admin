import phpserialize
from dataclasses import dataclass
from django.utils import dateparse
from apps.greencheck.models import Greencheck, GreenPresenting, GreencheckIp
from apps.accounts.models import Hostingprovider

import tld
import ipaddress
import logging

console = logging.StreamHandler()
logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARN)
# logger.addHandler(console)


@dataclass
class SiteCheck:
    """
    A representation of the Sitecheck object from the PHP app.
    We use it as a basis for logging to the Greencheck, but also maintaining
    our green_domains tables.
    """

    url: str
    ip: str
    data: bool
    green: bool
    hosting_provider_id: int
    checked_at: str
    match_type: str
    match_ip_range: int
    cached: bool
    checked_at: str


class LegacySiteCheckLogger:
    """
    A worker to consume messages from RabbiqMQ, generated by the
    enqueue library in the TGWF greencheck-api php app.

    Takes a PHP serialised data, and writes the necessary values
    to the greencheck logger tables.
    """

    php_dict = None

    def parse_serialised_php(self, body: bytes = None):
        """
        Accept a bytes string of encoded PHP, parses it returning
        a datastructure we can more easily parse
        """

        parsed_php = phpserialize.loads(body, object_hook=phpserialize.phpobject)
        result = parsed_php.get(b"result")
        self.php_dict = result._asdict()

        return self.php_dict

    def sitecheck_from_php_dict(self, body: bytes = None):
        """
        Accept a dict from parsed php, and return a datastructure without the name
        spacing.
        """
        php_dict = self.parse_serialised_php(body)

        return SiteCheck(
            ip=self.prefixed_attr("ip"),
            url=self.prefixed_attr("checkedUrl"),
            data=self.prefixed_attr("data"),
            green=self.prefixed_attr("green"),
            cached=self.prefixed_attr("cached"),
            hosting_provider_id=self.prefixed_attr("idHostingProvider"),
            match_type=self.prefixed_attr("matchtype").get("type"),
            match_ip_range=self.prefixed_attr("matchtype").get("id"),
            checked_at=self.prefixed_attr("checkedAt"),
        )

    def prefixed_attr(self, key):
        """
        Returns the value, as an appropriate type based what we
        find matching `key` in our phpdict:
        """

        # we have no dict parsed yet, return early
        if self.php_dict is None:
            return None

        prefix = "\x00TGWF\\Greencheck\\SitecheckResult\x00"
        full_length_key = f"{prefix}{key}"

        # we need to use bytes rather than a string for our key
        res = self.php_dict.get(full_length_key.encode())

        logger.debug(key)

        if key == "checkedAt":
            return self.get_checked_at(res)

        if key == "matchtype":
            return self.get_match_type(res)

        return self.cast_from_php(res)

    def cast_from_php(self, res):
        """
        Accept a value, and based on the type, return the tidier representation
        """
        if isinstance(res, bytes):
            return res.decode("utf-8")

        if isinstance(res, bool):
            return res

        if isinstance(res, int):
            return res

        if isinstance(res, dict):
            cleaned_res = {}
            for key, val in res.items():
                cleaned_res[key.decode("utf-8")] = self.cast_from_php(val)
            if "ipv4" or "ipv6" in cleaned_res.keys():
                # return just the ip address
                single_ip, *_ = [v for k, v in cleaned_res.items() if v]
                return single_ip

    def get_match_type(self, res=None):
        """
        Return the match type passed in. Because we can't be sure
        that the checked IP range still exists, we need to extract it
        now, rather than re-fetching it when adding it to the greencheck
        table.
        """
        cleaned_res = {}
        for key, val in res.items():
            cleaned_res[key.decode("utf-8")] = self.cast_from_php(val)

        return cleaned_res

    def get_checked_at(self, res):
        """
        Return the date of the check. Because the date is
        a dict, we need to fetch only the value we need.
        """
        # coerce the <phpobject b'DateTime'> to a dict
        date_dict = res._asdict()
        cleaned_res = {}

        for key, val in res._asdict().items():
            cleaned_res[key.decode("utf-8")] = self.cast_from_php(val)

        parsed_datetime = dateparse.parse_datetime(cleaned_res.get("date"))
        formatted_date = parsed_datetime.strftime("%Y-%m-%d %H:%M:%S")

        return formatted_date

    def parse_and_log_to_database(self, serialised_php):
        """
        Accept a message, like the kind sent over rabbitmq, and
        write it to the greencheck logging tables, as well as updating
        the green domain table if the checked site is green.
        """
        # fetch parse out our sitecheck
        sitecheck = self.sitecheck_from_php_dict(serialised_php)

        # log it our database and caches
        try:
            self.log_sitecheck_to_database(sitecheck)
        except Exception as err:
            logger.exception(f"Problem logging to our database: {err}")

    def log_sitecheck_to_database(self, sitecheck: SiteCheck):
        """
        Accept a sitecheck and log to the greencheck logging table,
        along with the green domains table (green_presenting).

        """
        logger.debug(sitecheck)

        try:
            hosting_provider = Hostingprovider.objects.get(
                pk=sitecheck.hosting_provider_id
            )
        except Hostingprovider.DoesNotExist:
            # if we have no hosting provider we leave it out
            hosting_provider = None

        if sitecheck.green and hosting_provider:
            self.update_green_domain_caches(sitecheck, hosting_provider)

        try:
            fixed_tld, *_ = (tld.get_tld(sitecheck.url, fix_protocol=True),)
        except tld.exceptions.TldDomainNotFound:

            try:
                ipaddress.ip_address(sitecheck.url)
                fixed_tld = ""
            except Exception:
                logger.exception("not a domain, or an IP address, not logging. Sitecheck results: {sitecheck}")
                return {
                    "status": "Error",
                    "sitecheck": sitecheck
                }

        except Exception:
            logger.exception("Unexpected error. Not logging the result. Sitecheck results: {sitecheck}")
            return {
                "status": "Error",
                "sitecheck": sitecheck
            }

        # finally write to the greencheck table

        if hosting_provider:
            res = Greencheck.objects.create(
                hostingprovider=hosting_provider.id,
                greencheck_ip=sitecheck.match_ip_range,
                date=dateparse.parse_datetime(sitecheck.checked_at),
                green="yes",
                ip=sitecheck.ip,
                tld=fixed_tld,
                type=sitecheck.match_type,
                url=sitecheck.url,
            )
            logger.debug(f"Greencheck logged: {res}")
        else:

            res = Greencheck.objects.create(
                date=dateparse.parse_datetime(sitecheck.checked_at),
                green="no",
                ip=sitecheck.ip,
                tld=fixed_tld,
                url=sitecheck.url,
            )
            logger.debug(f"Greencheck logged: {res}")

        # return result so we can inspect if need be
        return {
            "status": "OK",
            "sitecheck": sitecheck,
            "res": res
        }

    def update_green_domain_caches(
        self, sitecheck: SiteCheck, hosting_provider: Hostingprovider
    ):
        """
        Update the caches - namely the green domains table, and if running Redis
        """

        try:
            green_domain = GreenPresenting.objects.get(url=sitecheck.url)
        except GreenPresenting.DoesNotExist:
            green_domain = GreenPresenting(url=sitecheck.url)

        green_domain.hosted_by = hosting_provider.name
        green_domain.hosted_by_id = sitecheck.hosting_provider_id
        green_domain.hosted_by_website = hosting_provider.website
        green_domain.partner = hosting_provider.partner
        green_domain.modified = sitecheck.checked_at
        green_domain.green = sitecheck.green
        green_domain.save()
