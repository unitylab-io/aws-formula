{% from "aws/map.jinja" import aws with context %}
#!/usr/bin/env python

import boto.ec2
import boto.utils
import logging


# Set up the logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("aws:autoeips")
logging.getLogger("requests").setLevel(logging.WARNING)


class AutoEIP(object):
    filter_addresses = {{aws.eips}}
    ec2_connection = None
    instance_metadata = None

    def __init__(self):
        self.instance_metadata = self.get_instance_metadata()
        self.instance_id = self.instance_metadata.get('instance-id')
        # Collect details about this instance
        vpc_id = self.instance_metadata['network']['interfaces']['macs'].values()[0]['vpc-id']
        region = self.instance_metadata['placement']['availability-zone'][:-1]

        try:
            self.ec2_connection = boto.ec2.connect_to_region(region)
        except Exception as e:
            # This prints a user-friendly error with stacktrace
            print("Error getting EC2 conection: {}".format(e))

    def update_association(self, force=False):
        instance_associations = self.get_instance_association()
        if len(instance_associations) < 1 or force:
            print("Associating with any available eips")
            filtered_eips = self.get_unassociated_eips()
            self.associate_eip(filtered_eips)
        else:
            print("Already associated with EIP: {}".format(
                instance_associations[0]))

    def get_instance_association(self):
        instance_id = self.instance_metadata.get('instance-id', None)
        return self.ec2_connection.get_all_addresses(
            filters={'instance-id': instance_id})

    def get_instance_metadata(self):
        """
        Prints a mapping of private ip addresses to private dns names
        """
        try:
            return boto.utils.get_instance_metadata(timeout=5, num_retries=2)
        except Exception as e:
            sys.stderr.write("Error getting VPC ips: {}".format(e))
            return {}

    def associate_eip(self, eips, retries=3):
        if not self.instance_id:
            print "Error getting instance_id"
            return False
        for retry in range(retries):
            print "retry: {}".format(retry)
            for eip in eips:
                print "Associating instance: {} with eip: {}".format(
                    self.instance_id, eip.allocation_id)

                success = eip.associate(
                    instance_id=self.instance_id, allow_reassociation=False)
                if success:
                    return True

        return False

    def get_unassociated_eips(self):
        try:
            eips = self.ec2_connection.get_all_addresses(
                addresses=self.filter_addresses)

            unassociated_eips = \
                [eip for eip in eips if eip.association_id is None]

            print("Found {} eips: {}".format(len(eips), eips))
            print("Found {} unassociated eips: {}".format(
                len(unassociated_eips), unassociated_eips))

            return unassociated_eips

        except Exception as e:
            # This prints a user-friendly error with stacktrace
            logger.exception("Error getting EIPS: {}".format(e))
            return None


if __name__ == '__main__':
    autoeip = AutoEIP()
    autoeip.update_association()
