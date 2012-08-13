# This script is used to import the boundaries of police neighbourhoods and
# forces in England and Wales into MaPit. It takes KML data from
# http://www.police.uk/data and JSON data from the Police API (which is fetched by get-police-names.py), so you need those first.

import datetime
import HTMLParser
import json
import os
import re
import sys
import xml.sax

from xml.sax.handler import ContentHandler
from optparse import make_option

from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import *
from django.contrib.gis.geos import LinearRing, Polygon, MultiPolygon

from mapit.models import Area, Geometry, Generation, Country, Type, CodeType, NameType
from police_utils import PoliceLogger


logger = PoliceLogger()


def parse_police_names_json(names_path, options):
    """
    This parses the force and neighbourhood names from the API JSON files, and
    returns a dict like this:

    names_dict = {u'lancashire': (u'Lancashire Constabulary',
                                  {u'E37': u'Whalley',
                                   u'E36': u"Clitheroe East, Salthill & St Mary's",
                                   u'F23': u'Greensclough',
                                   u'F22': u'Greenfield',
                                   u'F21': u'Gawthorpe',
                                   ...
                                   }
                                  )
                  u'staffordshire': (u'Staffordshire Police',
                                     {u'IC40': u'Bradeley & Chell Heath',
                                      u'FW40': u'Wilnecote & Trinity',
                                      u'FV20': u'Chase Rural Neighbourhood',
                                      u'IE90': u'Abbey Hulton & Townsend',
                                      u'IE60': u'Springfields & Trent Vale',
                                      ...
                                      }
                                     )
                  ...
                  }
    """
    h = HTMLParser.HTMLParser()

    with open(os.path.join(names_path, 'forces.json')) as f:
        print 'Parsing names from API data'
        force_names = json.load(f)
        names_dict = {}
        for force in force_names:
            # Strangely, the JSON seems to contain HTML entities, so try to
            # unescape them:
            force['name'] = h.unescape(force['name'])
            if force['id'] in names_dict:
                raise Exception, "Force id %s found twice in JSON" % force['id']
            names_dict[force['id']] = (force['name'], {})
            if options['debug_data']:
                logger.log_code_and_name_max_lengths(force['id'],
                                                     force['name'])

    for force_id in names_dict.keys():
        with open(os.path.join(names_path, force_id+'_neighbourhoods.json')) as f:
            neighbourhood_names = json.load(f)
            for neighbourhood in neighbourhood_names:
                # As above, convert HTML entities:
                neighbourhood['name'] = h.unescape(neighbourhood['name'])
                if neighbourhood['id'] in names_dict[force_id][1]:
                    raise Exception, "Neighbourhood id %s found twice in force %s in JSON" % (neighbourhood['id'], force_id)
                names_dict[force_id][1][neighbourhood['id']] = neighbourhood['name']
                if options['debug_data']:
                    logger.log_code_and_name_max_lengths(neighbourhood['id'],
                                                         neighbourhood['name'])

    if options['debug_data']:
        logger.print_code_and_name_max_lengths()

    return names_dict

def too_tiny(linear_ring):
    '''
    Takes a linear ring, puts it in a polygon, transforms and simplifies it as
    area.html does when displaying an area on a map, and returns True if it is
    too small to be displayed and False otherwise.

    >>> too_tiny(LinearRing((0, 0), (0, 100), (100, 100), (100, 0), (0, 0)))
    False
    >>> too_tiny(LinearRing((533176.7676052941, 181046.6299361812), (533307.7457429301, 181040.88593647128), (533176.7676052982, 181046.62993618732), (533176.7676052941, 181046.6299361812)))
    True
    >>> too_tiny(LinearRing((533177, 181047), (533308, 181041), (533177, 181047), (533177, 181047)))
    True
    '''
    # This must be the same tolerance as area.html uses for displaying maps:
    tolerance = 0.0001
    new_srid = 4326
    # The Polygon appears to not know about the SRID unless it is specified here:
    original_poly = Polygon(linear_ring, srid=linear_ring.srid)
    transformed_poly = original_poly.transform(new_srid, clone=True)
    simplified_poly = transformed_poly.simplify(tolerance=tolerance)
    if simplified_poly.empty:
        return True
    return False

def get_displayable_polygon(polygon, force_code, neighbourhood_code):
    '''
    Takes a polygon and returns a new polygon, excluding any interior linear
    rings in the original geometry which are too small to be displayed on the map,
    or None if the outer boundary is too small to be displayed.
    '''
    if too_tiny(polygon[0]):
        print 'Outer boundary of polygon is too small to be displayed; ignoring this polygon'
        logger.log_outer_ring_too_tiny(force_code, neighbourhood_code, polygon[0].coords)
        return None
    rings = [ring for ring in polygon if not too_tiny(ring)]
    return Polygon(*rings)

def get_displayable_polygon_or_multipolygon(geometry, force_code, neighbourhood_code):
    '''
    Takes a polygon or multipolygon and returns a new geometry of the same type,
    excluding any interior linear rings in the original geometry which are too
    small to be displayed on the map.
    '''
    input_type = geometry.geom_type
    if input_type == 'Polygon':
        shapes = [geometry]
        holes_before = geometry.num_interior_rings
    elif input_type == 'MultiPolygon':
        shapes = geometry
        holes_before = sum(geometry.num_interior_rings for geometry in shapes)
    else:
        raise Exception, 'get_displayable_polygon_or_multipolygon expects a polygon or a multipolygon'

    # Discard all False values (here, None or any for which len(p) == 0):
    new_polys = filter(None,
                       (get_displayable_polygon(p, force_code, neighbourhood_code)
                           for p in shapes))

    if len(new_polys) == 1:
        new_geometry = new_polys[0]
        holes_after = new_geometry.num_interior_rings
    elif len(new_polys) > 1:
        new_geometry = MultiPolygon(*new_polys)
        holes_after = sum(poly.num_interior_rings for poly in new_geometry)
    else:
        new_geometry = None
        holes_after = '(no geometry to save)'

    if holes_before != holes_after:
        logger.log_removed_holes(force_code, neighbourhood_code, holes_before, holes_after)
        print  'Interior rings before:', holes_before
        print  'Interior rings after:', holes_after
    return new_geometry

def get_valid_polygon(feat):
    """
    This takes a GDAL feature, checks whether the geometry it contains is valid,
    and if not, tries to fix it using simplify(). It returns a valid OSGB (27700)
    GEOSGeometry polygon, a boolean value indicating whether the geometry was
    valid initially, and the number of co-ordinates in the initial geometry.
    """
    # Check that the feature is valid before transforming:
    geos_geometry = feat.geom.geos
    valid_before = geos_geometry.valid
    # Self-intersections and Ring Self-intersections seem to be generally
    # fixable by simplify(), but we want to know if any other types of
    # invalidity come up:
    if (not valid_before) and ('Self-intersection' not in geos_geometry.valid_reason):
        raise Exception, 'Invalid geometry found before transforming, and not a self-intersection'

    # feat is a GDAL feature
    ogr_g = feat.geom.transform(27700, clone=True)
    # ogr_g is an OGRGeometry polygon
    # ogr_g.geos returns a GEOSGeometry polygon, for
    # save_polygons_or_multipolygons:
    g = ogr_g.geos

    # We're assuming that transformation doesn't affect validity:
    if not valid_before:
        print '    Simplifying polygon'
        # This seems to create a new valid geometry (Polygon or
        # MultiPolygon) covering pretty much the same areas as the original
        # invalid one appears to. Many originally invalid polygons look as
        # though they have just one misplaced point; this tends to create a
        # new point at the self-intersection and remove the extra area, if
        # it is very small. This isn't a perfect fix, but it means that
        # unionagg() can use all neighbourhoods' polygons:

        g = g.simplify(preserve_topology=False)

        if not g.valid:
            raise Exception, 'Geometry still invalid after simplifying'

    return (g, valid_before, geos_geometry.num_coords)

def add_new_two_d_polygon(area, polygon):
    """
    This takes an Area and a GEOSGeometry polygon, and creates and returns a
    Geometry instance with a two-dimensional polygon for the area.
    """
    # XXX This doesn't check options['commit'], but should obviously only be
    # called when we do want to commit.
    # FIXME Check if polygons really need to be 2D now - must_be_two_d isn't in
    # save_polygons any more
    must_be_two_d = re.sub(r'([\d.-]+\s+[\d.-]+)(\s+[\d.-]+)(,|\)\))', r'\1\3', polygon.wkt)
    return area.polygons.create(polygon=must_be_two_d)

def save_polygons_or_multipolygons(area, geometry):
    """
    This takes an Area and a GEOSGeometry object, and saves the geometry (as one
    or more Geometry objects) to area.polygons.
    """
    # This is very similar to utils.save_polygons, but expects a GEOSGeometry
    # instead of an OGRGeometry.
    # XXX This doesn't check options['commit'], but should obviously only be
    # called when we do want to commit.
    if geometry.geom_type == 'MultiPolygon':
        shapes = geometry
    elif geometry.geom_type == 'Polygon':
        shapes = [geometry]
    else:
        raise Exception, "geometry for %s is neither a Polygon nor a MultiPolygon" % area
    area.polygons.all().delete()
    for polygon in shapes:
        new_polygon = add_new_two_d_polygon(area, polygon)

def update_or_create_area(code,
                          area_type,
                          country,
                          new_generation,
                          current_generation,
                          neighbourhood_area_type,
                          name_type,
                          name,
                          code_type,
                          force_code,
                          options,
                          feat=None,
                          parent_area=None):
    try:
        # Police neighbourhood codes are only guaranteed to be unique within
        # forces, not nationally, so parent_area is needed too.
        m = Area.objects.get(codes__code=code,
                             type=area_type,
                             parent_area=parent_area)
    except Area.DoesNotExist:
        m = Area(
            # name is set by Name.save():
            # name            = name,
            type            = area_type,
            country         = country,
            parent_area     = parent_area,
            generation_low  = new_generation,
            generation_high = new_generation,
        )

    # check that we are not about to skip a generation
    if m.generation_high and current_generation and m.generation_high.id < current_generation.id:
        raise Exception, "Area %s found, but not in current generation %s" % (m, current_generation)
    m.generation_high = new_generation

    # Force area polygons are updated separately later with a unionagg() of
    # their children's polygons:
    if area_type == neighbourhood_area_type:
        g, valid_before, num_coords = get_valid_polygon(feat)
        g = get_displayable_polygon_or_multipolygon(g, force_code, code)

    if options['debug_data'] and area_type == neighbourhood_area_type and valid_before == False:
        # Keep track of neighbourhood geometries which were invalid before
        # transforming:
        neighbourhood_code = code
        logger.log_invalid_polygon_before_transformation(num_coords, force_code, neighbourhood_code)

    if options['commit']:
        m.save()
        m.names.update_or_create({ 'type': name_type }, { 'name': name })
        m.codes.update_or_create({ 'type': code_type }, { 'code': code })
        if area_type == neighbourhood_area_type and g is not None:
            save_polygons_or_multipolygons(m, g)

    # m is an Area instance (which might be unsaved)
    # g is a GEOS Polygon or MultiPolygon
    return (m, g)


class Command(BaseCommand):
    help = 'Import police forces and neighbourhoods from KML files and names data from the police API'
    args = '<kml_path names_path>'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        ),
        make_option(
            '--debug_data',
            action="store_true",
            dest='debug_data',
            help='Save useful info about problems with the datasets',
        ),
        make_option(
            '--test',
            action="store_true",
            dest='doctests',
            help='Run doctests',
        ),
    )

    def handle(self, kml_path, names_path, **options):
        if options['doctests']:
            import doctest
            doctest.testmod(sys.modules[__name__])
            return

        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        # The May 2012 KML dataset includes '.DS_Store' in the root directory,
        # making os.listdir(kml_path) one longer than it was before:
        ignored = ('.DS_Store',)

        kml_forces_list = [force for force in os.listdir(kml_path) if force not in ignored]

        # names_path should contain an extra file for the names of all forces:
        if len(kml_forces_list) + 1 != len(os.listdir(names_path)):
            raise Exception, "The two datasets contain different numbers of forces!"

        names_dict = parse_police_names_json(names_path, options)

        # These are needed for both forces and neighbourhoods:
        neighbourhood_area_type = Type.objects.get(code='PON')
        force_area_type = Type.objects.get(code='POF')

        england = Country.objects.get(code='E')
        wales = Country.objects.get(code='W')

        name_type = NameType.objects.get(code='P')
        code_type = CodeType.objects.get(code='police_id')

        # The police API doesn't provide this information:
        # (assuming that forces don't cross the border...)
        welsh_forces = ('dyfed-powys', 'gwent', 'north-wales', 'south-wales')

        for force_code in kml_forces_list:

            if force_code in names_dict:
                force_name, force_names_dict = names_dict[force_code]
            else:
                raise Exception, "Name for force %s not found" % force_code
            print "Importing police force %s" % force_name

            if force_code in welsh_forces:
                country = wales
            else:
                country = england

#            country = wales if (force_code in welsh_forces) else england

            # Create the force, without any polygons for now:
            force, geom = update_or_create_area(code=force_code,
                                          area_type=force_area_type,
                                          country=country,
                                          new_generation=new_generation,
                                          current_generation=current_generation,
                                          neighbourhood_area_type=neighbourhood_area_type,
                                          name_type=name_type,
                                          name=force_name,
                                          code_type=code_type,
                                          force_code=force_code,
                                          options=options,
                                          feat=None,
                                          parent_area=None)


            # Start dealing with neighbourhoods in this force:
            neighbourhood_kmls_codes_list = []
            geometries_to_exclude = []

            force_directory = os.path.join(kml_path, force_code)

            for neighbourhood in os.listdir(force_directory):
                neighbourhood_code = re.sub('\.kml$', '', neighbourhood)

                if options['debug_data']:
                    # This is passed to logger.log_extra_names later:
                    neighbourhood_kmls_codes_list.append(neighbourhood_code)

                if neighbourhood_code in force_names_dict:
                    neighbourhood_name = force_names_dict[neighbourhood_code]
                else:
                    print "Name for %s in %s not found, using neighbourhood_code instead" % (neighbourhood_code, force_name)
                    neighbourhood_name = neighbourhood_code
                    if options['debug_data']:
                        logger.log_missing_name(force_code, neighbourhood_code)
                print "  Importing neighbourhood %s (%s) from %s" % (neighbourhood_name, neighbourhood_code, force_name)


                # Need to parse the KML manually to get the ExtendedData
                kml_data = KML()
                neighbourhood_kml = os.path.join(force_directory, neighbourhood)
                xml.sax.parse(neighbourhood_kml, kml_data)

                ds = DataSource(neighbourhood_kml)
                layer = ds[0]
                # FIXME No need at all to assume this:
                # Assume only one feat in layer:
                if len(layer) > 1:
                    raise Exception, "More than one feature in layer for %s (%s)" % (neighbourhood_code, force_name)
                feat = layer[0]

                neighbourhood, geom = update_or_create_area(code=neighbourhood_code,
                                          area_type=neighbourhood_area_type,
                                          country=country,
                                          new_generation=new_generation,
                                          current_generation=current_generation,
                                          neighbourhood_area_type=neighbourhood_area_type,
                                          name_type=name_type,
                                          name=neighbourhood_name,
                                          code_type=code_type,
                                          force_code=force_code,
                                          options=options,
                                          feat=feat,
                                          # parent_area needs to be set here,
                                          # rather than using find_parents.py:
                                          parent_area=force)

                if options['commit']:
                    # FIXME Getting these polygons only works when they have
                    # been saved to the database. Make this just use a list of
                    # unsaved polygons instead?

                    # unionagg() fails when invalid polygons are included, so keep
                    # track of them to exclude later:
                    # (I think there shouldn't be any invalid polygons by now,
                    # but keep this in anyway for now.)
                    for geometry in neighbourhood.polygons.all():
                        if not geometry.polygon.valid:
                            log_invalid_polygon_to_exclude(geometry.id, force_code, neighbourhood_code)
                            geometries_to_exclude.append(geometry.id)
                        else:
                            continue

            if options['debug_data']:
                logger.log_extra_names(force_code, neighbourhood_kmls_codes_list, force_names_dict)

            # unionagg() and collect() are GeoQueryset methods, so can't be used
            # if the polygons haven't been saved to the database:
            if options['commit']:
                # Create a force area geometry from its neighbourhood children,
                # excluding any polygons which are still invalid:
                valid_polys = Geometry.objects.filter(area__parent_area_id=force.id).exclude(id__in=geometries_to_exclude)
                print 'Trying to create a force geometry for %s' % force_code
                # unionagg() fails on some forces in the May 2012 dataset despite
                # all their children's polygons being valid (gloucestershire,
                # staffordshire, sussex, hampshire); it returns None for these.
                agg_methods = ('unionagg', 'simplified collect')
                for method in agg_methods:
                    try:
                        if method == 'unionagg':
                            print '  Trying unionagg()...'
                            force_geometry = valid_polys.unionagg()
                        elif method == 'simplified collect':
                            print '  Trying collect().simplify()...'
                            force_geometry = valid_polys.collect().simplify()
                        else:
                             raise Exception, "Unknown method: %s" % method
                        valid = force_geometry.valid
                        print '    force_geometry.valid:', valid
                        valid_reason = force_geometry.valid_reason
                    except AttributeError:
                        print '    %s() for %s returns None' % (method, force_name)
                        valid = False
                        valid_reason = 'Geometry is None'
                    if options['debug_data']:
                        logger.log_force_geometry_creation_attempt(force_code, method, valid, valid_reason)
                    if valid == True:
                        # Now we have a valid geometry to save:
                        break
                print force_geometry.geom_type
                force_geometry = get_displayable_polygon_or_multipolygon(force_geometry, force_code, 'force')
                # Assuming that there is still some kind of force_geometry:
                save_polygons_or_multipolygons(force, force_geometry)
            else:
                print '(not trying to create force geometries as --commit not specified)'


        if options['debug_data']:
            # Finally, print and save the logged data about problems with the
            # datasets:
            date = datetime.datetime.today()
            date_string = datetime.datetime.strftime(date, '%Y-%m-%d_%H:%M:%S')
            save_path = '../data/Police-data-problems_'+date_string+'/'
            if not os.access(save_path, os.F_OK):
                os.mkdir(save_path)

            print ''
            print '----------------------------------------'
            print ''
            logger.print_and_save_logged_data(save_path)


class KML(ContentHandler):
    def __init__(self, *args, **kwargs):
        self.content = ''
        self.data = {}

    def characters(self, content):
        self.content += content

    def endElement(self, name):
        if name == 'name':
            self.current = {}
            self.data[self.content.strip()] = self.current
        elif name == 'value':
            self.current[self.name] = self.content.strip()
            self.name = None
        self.content = ''

    def startElement(self, name, attr):
        if name == 'Data':
            self.name = attr['name']

