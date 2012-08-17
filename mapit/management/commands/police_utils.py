import json
import os

from mapit.models import Code, Name


class PoliceLogger(object):

    """
    Log details of problems in the KML and names datasets and save as JSON.
    """

    def __init__(self):
        self.code_max_length = 0
        self.name_max_length = 0
        self.invalid_before = [('num_coords', 'force_code', 'nbh_code')]
        self.invalid_polygons = [('force_code', 'nbh_code', 'geometry_id', 'num_polys')]
        self.nbh_polygons_not_updated = [('force_code', 'nbh_code')]
        self.outer_ring_too_tiny = [('force_code', 'nbh_code', 'ring_coords')]
        self.removed_holes = [('force_code', 'nbh_code', 'holes_before', 'holes_after')]
        self.missing_names = [('force_code', 'nbh_code')]
        self.extra_names = [('force_code', 'nbh_code', 'nbh_name')]

    def log_code_and_name_max_lengths(self, code, name):
        """
        Find the maximum lengths needed for the Code.code and Name.name fields.

        Find the maximum lengths of values to be saved in Code.code and
        Name.name, since this dataset has some very long ones which may require
        the fields' max_length to be increased again.
        """
        self.code_max_length = max(len(code), self.code_max_length)
        self.name_max_length = max(len(name), self.name_max_length)

    def print_code_and_name_max_lengths(self):
        """
        Print the maximum lengths needed for the Code.code and Name.name fields.
        """
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

    def log_invalid_polygon_before_transformation(self, num_coords, force_code, nbh_code):
        """
        Log a neighbourhood polygon which is initially invalid.

        This dataset contains some polygons which are invalid, due to
        Self-intersections or Ring Self-intersections. Log the number of points
        in these polygons in order to find the simplest one for testing ways of
        fixing them.
        """
        self.invalid_before.append((num_coords, force_code, nbh_code))

    def log_still_invalid_polygon(self, force_code, nbh_code, geometry_id, num_polys):
        """
        Log an unfixably invalid neighbourhood polygon.

        Log a neighbourhood polygon which is still invalid after attempting to
        fix it using simplify(), and therefore is excluded from the queryset to
        be aggregated for the force geometry.

        Also log the total number of polygons which were produced for this
        neighbourhood, so that we can see if they were all still invalid
        """
        self.invalid_polygons.append((force_code, nbh_code, geometry_id, num_polys))

    def log_nbh_polygons_not_updated(self, force_code, nbh_code):
        """
        Log a neighbourhood for which no new polygons could be created.

        If no new geometry could be created for a neighbourhood, then any
        previously existing polygons for it were left in place and not deleted.
        """
        self.nbh_polygons_not_updated.append((force_code, nbh_code))

    def log_outer_ring_too_tiny(self, force_code, nbh_code, ring_coords):
        """
        Log a geometry which was too small to be displayed and was discarded.

        If the outer boundary ring of a polygon is too small to be displayed on
        the map, the polygon is not saved. I expect these to be tiny areas
        created by simplifying originally invalid neighbourhood geometries.

        nbh_code is 'force' when the geometry is a force geometry.
        """
        self.outer_ring_too_tiny.append((force_code, nbh_code, ring_coords))

    def log_removed_holes(self, force_code, nbh_code, holes_before, holes_after):
        """
        Log a geometry which contained tiny holes which were removed.

        Very small inner rings make a polygon undisplayable on the map, because
        the simplification tolerance specified in area.html causes the polygon
        returned in the response by area_polygon to be empty. Removing these
        small holes manually makes the polygon displayable.

        I expect these to be tiny holes created by unionagg() in force
        geometries where neighbourhood boundaries don't match up, or by
        simplifying invalid neighbourhood polygons.
        """
        self.removed_holes.append((force_code, nbh_code, holes_before, holes_after))

    def log_missing_name(self, force_code, nbh_code):
        """
        Log a neighbourhood for which no name exists in the API dataset.
        """
        self.missing_names.append((force_code, nbh_code))

    def log_extra_names(self, force_code, nbh_kmls_codes_list, force_names_dict):
        """
        Log neighbourhood names in the API dataset with no matching KML.

        This is called once per force.
        """
        nbh_kmls_codes_set = set(nbh_kmls_codes_list)
        nbh_names_codes_set = set(force_names_dict.keys())
        extra_codes_set = nbh_names_codes_set - nbh_kmls_codes_set
        for nbh_code in extra_codes_set:
            self.extra_names.append((force_code,
                                     nbh_code,
                                     # neighbourhood name:
                                     force_names_dict[nbh_code]))

    def save_data_to_json(self, save_path, basename, data):
        """
        Serialize one type of logged data to JSON and save it.
        """
        with open(os.path.join(save_path, basename+'.json'), 'w') as f:
            json.dump(data, f, indent=4)

    def print_and_save_logged_data(self, save_path):

        """
        Print summaries of the logged data, and serialize and save it all.
        """

        self.print_code_and_name_max_lengths()
        print ''

        if self.invalid_before:
            # Sort invalid_before by num_coords to find the simplest initially
            # invalid polygon for testing purposes:
            simplest = min(self.invalid_before[1:])
            print 'Simplest polygon which was invalid straight after loading it from the KML:'
            print '  force code:', simplest[1]
            print '  neighbourhood code:', simplest[2]
            print '  number of points:', simplest[0]
            print ''

        data_to_process = (
            {'basename': 'invalid_before',
             'message': '%d features invalid before transformation' % (len(self.invalid_before) - 1)},
            {'basename': 'invalid_polygons',
             'message': "%d neighbourhood polygons are still invalid and were excluded from their forces' polygons" % (len(self.invalid_polygons) - 1)},
            {'basename': 'nbh_polygons_not_updated',
             'message': "Polygons for %d neighbourhoods could not be updated" % (len(self.nbh_polygons_not_updated) - 1)},
            {'basename': 'outer_ring_too_tiny',
             'message': "%d polygons were too small to be displayed on the map and were not saved" % (len(self.outer_ring_too_tiny) - 1)},
            {'basename': 'removed_holes',
             'message': "%d polygons contained holes which were too small to be displayed on the map and were removed" % (len(self.removed_holes) - 1)},
            {'basename': 'missing_names',
             'message': 'Names were missing for %d neighbourhoods' % (len(self.missing_names) - 1)},
            {'basename': 'extra_names',
             'message': '%d extra neighbourhood names were found' % (len(self.extra_names) - 1)},
        )

        print 'Logged data is saved in %s/' % save_path
        for i in data_to_process:
            basename = i['basename']
            message = i['message']
            stored_data = getattr(self, basename)
            print message
            print '    (see %s.json)' % basename
            self.save_data_to_json(save_path, basename, stored_data)

