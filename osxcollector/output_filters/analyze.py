#!/usr/bin/env python
# -*- coding: utf-8 -*-
from optparse import OptionParser

import simplejson
from osxcollector.output_filters.base_filters.chain import ChainFilter
from osxcollector.output_filters.base_filters.output_filter import OutputFilter
from osxcollector.output_filters.base_filters.output_filter import run_filter
from osxcollector.output_filters.chrome_history import ChromeHistoryFilter
from osxcollector.output_filters.find_blacklisted import FindBlacklistedFilter
from osxcollector.output_filters.find_domains import FindDomainsFilter
from osxcollector.output_filters.firefox_history import FirefoxHistoryFilter
from osxcollector.output_filters.opendns. \
    lookup_domains import LookupDomainsFilter as OpenDnsLookupDomainsFilter
from osxcollector.output_filters.opendns. \
    related_domains import RelatedDomainsFilter as OpenDnsRelatedDomainsFilter
from osxcollector.output_filters.related_files import RelatedFilesFilter
from osxcollector.output_filters.virustotal. \
    lookup_domains import LookupDomainsFilter as VtLookupDomainsFilter
from osxcollector.output_filters.virustotal. \
    lookup_hashes import LookupHashesFilter as VtLookupHashesFilter


class AnalyzeFilter(ChainFilter):

    def __init__(self, initial_file_terms=None, initial_domains=None, initial_ips=None):
        filter_chain = [
            # Find suspicious stuff
            FindDomainsFilter(),
            FindBlacklistedFilter(),

            # Find stuff related to suspicious stuff
            RelatedFilesFilter(initial_terms=initial_file_terms, when=is_on_blacklist),
            OpenDnsRelatedDomainsFilter(initial_domains=initial_domains, initial_ips=initial_ips),

            # Lookup threat info on suspicious and related stuff
            OpenDnsLookupDomainsFilter(is_suspicious_when=is_suspicious),
            VtLookupDomainsFilter(only_lookup_when=is_suspicious),
            VtLookupHashesFilter(only_lookup_when=is_suspicious),

            # Sort browser history for maximum pretty
            FirefoxHistoryFilter(),
            ChromeHistoryFilter(),

            # Summarize what has happened
            _SummaryOutputFilter(),
        ]
        super(AnalyzeFilter, self).__init__(filter_chain)


def is_suspicious(blob):
    return 'osxcollector_blacklist' in blob or 'osxcollector_related' in blob or 'quarantinues' == blob['osxcollector_section']


def is_on_blacklist(blob):
    return 'osxcollector_blacklist' in blob


def include_in_summary(blob):
    interesting_keys = ['osxcollector_blacklist', 'osxcollector_related', 'osxcollector_opendns', 'osxcollector_virustotal']
    return any([key in blob for key in interesting_keys])


class _SummaryOutputFilter(OutputFilter):

    def __init__(self):
        super(_SummaryOutputFilter, self).__init__()
        self._all_blobs = list()

    def filter_line(self, blob):
        """Each Line of osxcollector output will be passed to filter_line.

        The OutputFilter should return the line, either modified or unmodified.
        The OutputFilter can also choose to return nothing, effectively swalling the line.

        Args:
            output_line: A dict

        Returns:
            A dict or None
        """
        self._all_blobs.append(blob)
        return None

    def end_of_lines(self):
        """Called after all lines have been fed to filter_output_line.

        The OutputFilter can do any batch processing on that requires the complete input.

        Returns:
            An array of dicts (empty array if no lines remain)
        """
        with open('./analyze.json', 'w') as fp:
            for blob in self._all_blobs:
                if include_in_summary(blob):
                    fp.write(simplejson.dumps(blob))
                    fp.write('\n')

        return self._all_blobs


def main():
    parser = OptionParser(usage='usage: %prog [options]')
    parser.add_option('-f', '--file-term', dest='file_terms', default=[], action='append',
                      help='[OPTIONAL] Suspicious terms to use in pivoting through file names.  May be specified more than once.')
    parser.add_option('-d', '--domain', dest='domain_terms', default=[], action='append',
                      help='[OPTIONAL] Suspicious domains to use for pivoting.  May be specified more than once.')
    parser.add_option('-i', '--ip', dest='ip_terms', default=[], action='append',
                      help='[OPTIONAL] Suspicious IP to use for pivoting.  May be specified more than once.')
    options, _ = parser.parse_args()

    run_filter(AnalyzeFilter(initial_file_terms=options.file_terms, initial_domains=options.domain_terms, initial_ips=options.ip_terms))


if __name__ == "__main__":
    main()