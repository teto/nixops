# -*- coding: utf-8 -*-

# Automatic provisioning of Azure reserved IP addresses.

import os
import azure
import time

from nixops.util import attr_property
from nixops.azure_common import ResourceDefinition, ResourceState


class AzureReservedIPAddressDefinition(ResourceDefinition):
    """Definition of an Azure Reserved IP Address"""

    @classmethod
    def get_type(cls):
        return "azure-reserved-ip-address"

    def __init__(self, xml):
        ResourceDefinition.__init__(self, xml)

        self.reserved_ip_address_name = self.get_option_value(xml, 'name', str)
        self.copy_option(xml, 'location', str)
        self.copy_option(xml, 'label', str)

    def show_type(self):
        return "{0} [{1}]".format(self.get_type(), self.location)


class AzureReservedIPAddressState(ResourceState):
    """State of an Azure Reserved IP Address"""

    reserved_ip_address_name = attr_property("azure.name", None)
    location = attr_property("azure.location", None)
    label = attr_property("azure.label", None)
    ip_address = attr_property("azure.ipAddress", None)
    azure_id = attr_property("azure.id", None)

    @classmethod
    def get_type(cls):
        return "azure-reserved-ip-address"

    def __init__(self, depl, name, id):
        ResourceState.__init__(self, depl, name, id)

    def show_type(self):
        s = super(AzureReservedIPAddressState, self).show_type()
        if self.state == self.UP: s = "{0} [{1}]".format(s, self.location)
        return s

    @property
    def resource_id(self):
        return self.reserved_ip_address_name

    nix_name = "azureReservedIPAddresses"

    @property
    def full_name(self):
        return "Azure reserved IP address '{0}'".format(self.reserved_ip_address_name)

    @property
    def public_ipv4(self):
        return self.ip_address

    def get_resource(self):
        try:
            return self.sms().get_reserved_ip_address(self.reserved_ip_address_name)
        except azure.WindowsAzureMissingResourceError:
            return None

    def destroy_resource(self):
        self.sms().delete_reserved_ip_address(self.reserved_ip_address_name)

    defn_properties = [ 'label', 'location' ]

    def create(self, defn, check, allow_reboot, allow_recreate):
        self.no_property_change(defn, 'location')
        self.no_property_change(defn, 'label')

        self.copy_credentials(defn)
        self.reserved_ip_address_name = defn.reserved_ip_address_name

        if check:
            address = self.get_settled_resource()
            if not address:
                self.warn_missing_resource()
            elif self.state == self.UP:
                self.handle_changed_property('location', address.location, can_fix = False)
                self.handle_changed_property('label', address.label, can_fix = False)
                self.handle_changed_property('ip_address', address.address, property_name = '')
                self.handle_changed_property('azure_id', address.id, can_fix = False)
            else:
                self.warn_not_supposed_to_exist(valuable_resource = True)
                self.confirm_destroy()

        if self.state != self.UP:
            if self.get_settled_resource():
                raise Exception("tried creating a reserved IP address that already exists; "
                                "please run 'deploy --check' to fix this")

            self.log("creating {0} in {1}...".format(self.full_name, defn.location))
            self.sms().create_reserved_ip_address(defn.reserved_ip_address_name,
                                                  label = defn.label,
                                                  location = defn.location)
            time.sleep(10) #FIXME: create_reserved_ip_address should have been an async request
            address = self.get_settled_resource()
            self.state = self.UP
            self.copy_properties(defn)
            self.ip_address = address.address
            self.azure_id = address.id