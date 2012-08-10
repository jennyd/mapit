import json

from mapit.models import Code, Name


class PoliceLogger(object):
    def __init__(self):
        self.code_max_length = 0
        self.name_max_length = 0
        self.invalid_before = []
        self.invalid_polygons = {}
        self.outer_ring_too_tiny = []
        self.removed_holes = []
        self.missing_names = []
        self.extra_names = []
        self.force_geometry_creation_attempts = []

    def log_code_and_name_max_lengths(self, code, name):
        '''Find the maximum lengths of values to be saved in Code.code and
        Name.name, since this dataset has some very long ones which may require
        the fields' max_length to be increased again.
        '''
        self.code_max_length = max(len(code), self.code_max_length)
        self.name_max_length = max(len(name), self.name_max_length)

    def print_code_and_name_max_lengths(self):
        try:
            existing_code_max_length = Code._meta.get_field('code').max_length
        except:
            existing_code_max_length = None
        try:
            existing_name_max_length = Name._meta.get_field('name').max_length
        except:
            existing_name_max_length = None

        print 'Maximum length required for Code.code:', self.code_max_length
        print '    (currently set to', str(existing_code_max_length)+')'
        print 'Maximum length required for Name.name:', self.name_max_length
        print '    (currently set to', str(existing_name_max_length)+')'

    def log_invalid_polygon_before_transformation(self, num_coords, force_code, neighbourhood_code):
        '''Store details of a neighbourhood polygon which is invalid when it is
        extracted from the KML file.
        '''
        self.invalid_before.append((num_coords, force_code, neighbourhood_code))

    def log_invalid_polygon_to_exclude(self, geometry_id, force_code, neighbourhood_code):
        '''Store details of a neighbourhood polygon which is still invalid after
        transformation and simplification, and therefore needs to be excluded
        from the queryset to be aggregated for the force geometry.
        '''
        # This requires the geometry to be saved and have an id, and uses the id
        # as the key, which is reasonable at the moment since keys() is used to
        # filter a queryset:
        self.invalid_polygons[geometry.id] = (force_code, neighbourhood_code)

    def log_outer_ring_too_tiny(self, force_code, neighbourhood_code, ring_coords):
        '''Store details of geometries in which the outer boundary ring of a
        polygon is too small to be displayed on the map. neighbourhood_code is
        'force' for forces. (I expect these to be tiny areas created by
        simplifying originally invalid neighbourhood geometries.)
        '''
        self.outer_ring_too_tiny.append((force_code, neighbourhood_code, ring_coords))

    def log_removed_holes(self, force_code, neighbourhood_code, holes_before, holes_after):
        self.removed_holes.append((force_code, neighbourhood_code, holes_before, holes_after))

    def log_missing_name(self, force_code, neighbourhood_code):
        '''Store details of a neighbourhood for which there is no name in the
        API dataset. This is called once per neighbourhood.
        '''
        self.missing_names.append((force_code, neighbourhood_code))

    def log_extra_names(self, force_code, neighbourhood_kmls_codes_list, force_names_dict):
        '''Store extra neighbourhood names from the API dataset whose codes do
        not match any in the KMLs dataset. This is called once per force.
        '''
        neighbourhood_kmls_codes_set = set(neighbourhood_kmls_codes_list)
        neighbourhood_names_codes_set = set(force_names_dict.keys())
        extra_codes_set = neighbourhood_names_codes_set - neighbourhood_kmls_codes_set
        for neighbourhood_code in extra_codes_set:
            self.extra_names.append((force_code,
                                     neighbourhood_code,
                                     # neighbourhood name:
                                     force_names_dict[neighbourhood_code]))

    def log_force_geometry_creation_attempt(self, force_code, method, successful, valid_reason):
        '''Store a force code, the aggregation method attempted, whether it
        was successful, and, if a geometry was created but was invalid, the
        reason for it being invalid.
        '''
        self.force_geometry_creation_attempts.append((force_code, method, successful, valid_reason))

    def save_data_to_json(self, save_path, basename, data):
        with open(os.path.join(save_path, basename+'.json'), 'w') as f:
#            print '  Saving %s.json' % basename
            json.dump(data, f, indent=4)

    def print_and_save_logged_data(self, save_path):
        self.print_code_and_name_max_lengths()

        # Sort invalid_before by num_coords to find the simplest initially
        # invalid polygon for testing purposes:
        simplest = min(self.invalid_before)
        print 'Simplest polygon which was invalid straight after loading it from the KML:'
        print '  force code:', simplest[1]
        print '  neighbourhood code:', simplest[2]
        print '  number of points:', simplest[0]

        data_to_process = (
            {'basename': 'invalid_before',
             'message': '%d features invalid before transformation' % len(self.invalid_before)},
            {'basename': 'invalid_polygons',
             'message': "%d neighbourhood polygons are invalid and were excluded from their forces' polygons" % len(self.invalid_polygons.keys())},
            {'basename': 'outer_ring_too_tiny',
             'message': "%d polygons were too small to be displayed on the map and were not saved" % len(self.outer_ring_too_tiny)},
            {'basename': 'removed_holes',
             'message': "%d polygons contained holes which were too small to be displayed on the map and were removed" % len(self.removed_holes)},
            {'basename': 'missing_names',
             'message': 'Names were missing for %d neighbourhoods' % len(self.missing_names)},
            {'basename': 'extra_names',
             'message': '%d extra neighbourhood names were found' % len(self.extra_names)},
            {'basename': 'force_geometry_creation_attempts',
             'message': 'A total of %d attempts were made to create force geometries' % len(self.force_geometry_creation_attempts)}
        )

        for i in data_to_process:
            basename = i['basename']
            message = i['message']
            stored_data = getattr(self, basename)
            print message
            print '    (see %s%s.json)' % (save_path, basename)
            self.save_data_to_json(save_path, basename, stored_data)

