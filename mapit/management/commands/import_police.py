# This script is used to import the boundaries of police neighbourhoods and
# forces in England and Wales into MaPit. It takes KML data from
# http://www.police.uk/data and JSON data from the Police API (which is fetched
# by get-police-names.py), so you need those first.

import datetime
import doctest
import HTMLParser
import json
import os
import re
import sys

from optparse import make_option

from django.core.management.base import BaseCommand

from django.contrib.gis.gdal import *
from django.contrib.gis.geos import LinearRing, Polygon, MultiPolygon

from mapit.models import Area, Geometry, Generation, Country, Type, CodeType, NameType
from police_utils import PoliceLogger


logger = None


def parse_police_names_json(names_path, options):

    """
    Parse the names data from the API JSON files, and return it in a dict.

    Return a dict like this:

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
    names_dict = {}

    def parse_names_file(filename, lookup_dict):
        with open(os.path.join(names_path, filename)) as f:
            names = json.load(f)
        for n in names:
            # Strangely, the JSON seems to contain HTML entities, so try to
            # unescape them:
            n['name'] = h.unescape(n['name'])
            if n['id'] in lookup_dict:
                raise Exception, "ID '%s' found twice in %s" % (n['id'], filename)
            lookup_dict[n['id']] = (n['name'], {}) if (filename == 'forces.json') else n['name']
            if logger:
                logger.log_code_and_name_max_lengths(n['id'], n['name'])

    print "Parsing names from API data"
    parse_names_file('forces.json', names_dict)
    for force_id in names_dict.keys():
        parse_names_file(force_id+'_neighbourhoods.json', names_dict[force_id][1])

    if logger:
        logger.print_code_and_name_max_lengths()

    return names_dict

def make_iterable_shapes(geometry):
    """
    Make an iterable sequence of polygons from a geometry.

    Take a GEOS Polygon or MultiPolygon, and return an iterable whose elements
    are GEOS Polygons.
    """
    input_type = geometry.geom_type
    if input_type == 'MultiPolygon':
        shapes = geometry
    elif input_type == 'Polygon':
        shapes = [geometry]
    else:
        raise Exception, "Geometry is neither a GEOS Polygon nor a GEOS MultiPolygon"
    return shapes

def too_tiny(linear_ring):
    """
    Determine if a linear ring is too small to be displayed on the map.

    Take a GEOSGeometry LinearRing, put it in a polygon, transform and simplify
    it as area.html does when displaying an area on a map, and return True if it
    is too small to be displayed and False otherwise.

    >>> too_tiny(LinearRing((0, 0), (0, 100), (100, 100), (100, 0), (0, 0), srid=27700))
    False
    >>> too_tiny(LinearRing((533176.7676052941, 181046.6299361812), (533307.7457429301, 181040.88593647128), (533176.7676052982, 181046.62993618732), (533176.7676052941, 181046.6299361812), srid=27700))
    True
    >>> too_tiny(LinearRing((533177, 181047), (533308, 181041), (533177, 181047), (533177, 181047), srid=27700))
    True
    """
    # This must be the same tolerance as area.html uses for displaying maps:
    tolerance = 0.0001
    new_srid = 4326
    # GEOSGeometry needs the SRID to be set explicitly:
    original_poly = Polygon(linear_ring, srid=linear_ring.srid)
    transformed_poly = original_poly.transform(new_srid, clone=True)
    simplified_poly = transformed_poly.simplify(tolerance=tolerance)
    if simplified_poly.empty:
        return True
    return False

def get_displayable_polygon(polygon, force_code, nbh_code):

    """
    Take a polygon and return it as a displayable polygon.

    Take a GEOSGeometry polygon and return a new polygon, excluding any interior
    rings in the original geometry which are too small to be displayed on the map,
    or return None if the outer boundary is too small to be displayed.
    """

    if too_tiny(polygon[0]):
        print "Outer boundary of polygon is too small to be displayed; ignoring this polygon"
        if logger:
            logger.log_outer_ring_too_tiny(force_code, nbh_code, polygon[0].coords)
        return None
    return Polygon(*[ring for ring in polygon if not too_tiny(ring)])

def get_displayable_polygon_or_multipolygon(geometry, force_code, nbh_code):

    """
    Take a Polygon or MultiPolygon and return it as a displayable geometry.

    Take a GEOSGeometry Polygon or MultiPolygon and return it as a new geometry,
    excluding any linear rings in the original geometry which are too small to
    be displayed on the map.
    """

    shapes = make_iterable_shapes(geometry)
    holes_before = sum(geometry.num_interior_rings for geometry in shapes)

    # Discard all False values (here, these are None or any for which len(p) == 0):
    new_polys = filter(None,
                       (get_displayable_polygon(p, force_code, nbh_code)
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
        if logger:
            logger.log_removed_holes(force_code, nbh_code, holes_before, holes_after)
        print  'Interior rings before:', holes_before
        print  'Interior rings after:', holes_after
    return new_geometry

def get_valid_polygon(feat):

    """
    Take a GDAL feature and return a valid transformed geometry from it.

    Take a GDAL feature, check whether the geometry it contains is valid,
    and if not, try to fix it using simplify(). Return a valid OSGB (27700)
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
        raise Exception, "Invalid geometry found before transforming, and not a self-intersection"

    # feat is a GDAL feature
    ogr_g = feat.geom.transform(27700, clone=True)
    # ogr_g is an OGRGeometry polygon
    # ogr_g.geos returns a GEOSGeometry polygon, for save_geos_polygons:
    g = ogr_g.geos

    # We're assuming that transformation doesn't affect validity:
    if not valid_before:
        print "    Simplifying polygon"
        # This seems to create a new valid geometry (Polygon or
        # MultiPolygon) covering pretty much the same areas as the original
        # invalid one appears to. Many originally invalid polygons look as
        # though they have just one misplaced point; this tends to create a
        # new point at the self-intersection and remove the extra area, if
        # it is very small. This isn't a perfect fix, but it means that
        # unionagg() can use all neighbourhoods' polygons:

        g = g.simplify(preserve_topology=False)

        if not g.valid:
            raise Exception, "Geometry still invalid after simplifying"

    return (g, valid_before, geos_geometry.num_coords)

def save_geos_polygons(area, geometry):

    """
    Save a geometry to an Area's polygons.

    Take an Area and a GEOSGeometry object, save the geometry (as one or more
    Geometry objects) to area.polygons, and return a list of tuples of
    Polygons and their Geometry IDs.
    """

    # This is similar to utils.save_polygons, but expects a GEOSGeometry
    # instead of an OGRGeometry.
    # This doesn't check options['commit'], but should obviously only be
    # called when we do want to commit.

    shapes = make_iterable_shapes(geometry)
    area.polygons.all().delete()
    new_geometries = []
    for polygon in shapes:
        new_polygon = area.polygons.create(polygon=polygon.wkt)
        new_geometries.append((new_polygon.polygon, new_polygon.id))
    return new_geometries

def update_or_create_area(code,
                          area_type,
                          country,
                          new_generation,
                          current_generation,
                          nbh_area_type,
                          name_type,
                          name,
                          code_type,
                          force_code,
                          options,
                          feat=None,
                          parent_area=None):

    """
    Get an existing Area or create a new one, and update it and its related objects.

    Identify an existing Area or create a new one, and update it. If the area is
    a neighbourhood, try to extract a valid, displayable geometry from a GDAL
    Feature for it. If the --commit option is given, save the area along with
    its names, codes and polygons. Return the Area, which may be unsaved if
    --commit is not specified.
    """
    try:
        # Police neighbourhood codes are only guaranteed to be unique within
        # forces, not nationally, so parent_area is needed too:
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

    new_geometries = []
    if area_type == nbh_area_type:
        g, valid_before, num_coords = get_valid_polygon(feat)
        g = get_displayable_polygon_or_multipolygon(g, force_code, code)
        if logger:
            if valid_before == False:
                # Keep track of neighbourhood geometries which were invalid before
                # transforming:
                logger.log_invalid_polygon_before_transformation(num_coords,
                                                                 force_code,
                                                                 code)
            if not g:
                # There are no new polygons for this neighbourhood, so any
                # existing ones will be left in the database, since there is
                # nothing to replace them with:
                logger.log_nbh_polygons_not_updated(force_code, code)
        if g and (not options['commit']):
            # If we have a geometry and are committing, new_geometries will
            # be made later.
            shapes = make_iterable_shapes(g)
            # We don't have a geometry ID because we're not committing:
            new_geometries = [(polygon, None) for polygon in shapes]

    else:
        # Force area polygons are updated separately later by aggregating
        # their children's polygons:
        g = None

    if options['commit']:
        m.save()
        m.names.update_or_create({ 'type': name_type }, { 'name': name })
        m.codes.update_or_create({ 'type': code_type }, { 'code': code })
        if area_type == nbh_area_type and g is not None:
            new_geometries = save_geos_polygons(m, g)

    if new_geometries:
        num_polys = len(new_geometries)
        for tup in new_geometries:
            polygon, geometry_id = tup
            if polygon.valid:
                continue

            # unionagg() fails when invalid polygons are included, so keep track
            # of them to exclude later.

            # I think that all invalid polygons are being fixed, but I'm leaving
            # this in anyway for now. I also can't think of a way in which an
            # area could have a mixture of valid and invalid polygons, so
            # num_polys probably doesn't tell us anything helpful that we don't
            # already know.

            if options['commit']:
                geometries_to_exclude.append(geometry_id)
            if logger:
                # geometry_id will be None if we're not committing,
                # so log the total number of polygons for this
                # neighbourhood too:
                logger.log_still_invalid_polygon(force_code,
                                                 nbh_code,
                                                 geometry_id,
                                                 num_polys)

    # m is a new or updated Area (which might be unsaved)
    return m


class Command(BaseCommand):
    help = 'Import police forces and neighbourhoods from KML files and names data from the police API'
    args = '<kml_path> <names_path>'
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
            doctest.testmod(sys.modules[__name__])
            return

        if options['debug_data']:
            global logger
            logger = PoliceLogger()

        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        # The May 2012 KML dataset includes '.DS_Store' in the root directory,
        # making os.listdir(kml_path) one longer than it was before:
        ignored = ('.DS_Store', 'README')

        kml_forces_list = [force for force in os.listdir(kml_path) if force not in ignored]

        # The three extra items in names_path are:
        #   - forces.json, an extra file for the names of all forces.
        #   - data for neighbourhoods in Northern Ireland, which was recently
        #     added to the API (between 31/07/2012 and 16/08/2012), but no KMLs
        #     are available yet, so we are ignoring these for now.
        #     log_extra_names doesn't log these names either.
        #   - README - both dataset directories contain READMEs with licence
        #     information but the KMLs one has already been excluded from
        #     kml_forces_list.
        if len(kml_forces_list) + 3 != len(os.listdir(names_path)):
            raise Exception, "The two datasets contain different numbers of forces!"

        names_dict = parse_police_names_json(names_path, options)

        # These are needed for both forces and neighbourhoods:
        nbh_area_type = Type.objects.get(code='PON')
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

            country = wales if (force_code in welsh_forces) else england

            # Create the force, without any polygons for now. We need a force
            # area to use as parent_area for its neighbourhood children.
            force = update_or_create_area(code=force_code,
                                          area_type=force_area_type,
                                          country=country,
                                          new_generation=new_generation,
                                          current_generation=current_generation,
                                          nbh_area_type=nbh_area_type,
                                          name_type=name_type,
                                          name=force_name,
                                          code_type=code_type,
                                          force_code=force_code,
                                          options=options,
                                          feat=None,
                                          parent_area=None)


            # Start dealing with neighbourhoods in this force:
            nbh_kmls_codes_list = []
            geometries_to_exclude = []

            force_directory = os.path.join(kml_path, force_code)

            for nbh in os.listdir(force_directory):
                nbh_code = re.sub('\.kml$', '', nbh)

                if logger:
                    # This is passed to logger.log_extra_names later:
                    nbh_kmls_codes_list.append(nbh_code)

                if nbh_code in force_names_dict:
                    nbh_name = force_names_dict[nbh_code]
                else:
                    print "Name for %s in %s not found, using neighbourhood code instead" % (nbh_code, force_name)
                    nbh_name = nbh_code
                    if logger:
                        logger.log_missing_name(force_code, nbh_code)
                print "  Importing neighbourhood %s (%s) from %s" % (nbh_name, nbh_code, force_name)

                ds = DataSource(os.path.join(force_directory, nbh))
                layer = ds[0]
                if len(layer) > 1:
                    # In fact, it shouldn't be a problem to deal with this, but
                    # it doesn't currently arise, so throw an exception so that
                    # we notice:
                    raise Exception, "More than one feature in layer for %s (%s)" % (nbh_code, force_name)
                feat = layer[0]

                update_or_create_area(code=nbh_code,
                                      area_type=nbh_area_type,
                                      country=country,
                                      new_generation=new_generation,
                                      current_generation=current_generation,
                                      nbh_area_type=nbh_area_type,
                                      name_type=name_type,
                                      name=nbh_name,
                                      code_type=code_type,
                                      force_code=force_code,
                                      options=options,
                                      feat=feat,
                                      # parent_area needs to be set here,
                                      # rather than using find_parents.py:
                                      parent_area=force)


            # Finish processing this force:

            if logger:
                logger.log_extra_names(force_code, nbh_kmls_codes_list, force_names_dict)

            # unionagg() is a GeoQueryset method, so can't be used to create a
            # force geometry if the polygons haven't been saved to the database:
            if not options['commit']:
                print "(not trying to create force geometries as --commit not specified)"
                continue

            # Create a force area geometry from its neighbourhood children,
            # excluding any polygons which are still invalid:
            valid_polys = Geometry.objects.filter(area__parent_area_id=force.id).exclude(id__in=geometries_to_exclude)
            print "Trying to create a force geometry for %s" % force_name

            force_geometry = valid_polys.unionagg()
            if not force_geometry:
                raise Exception, "Failed to create a force geometry for %s" % force_name

            displayable_force_geometry = get_displayable_polygon_or_multipolygon(force_geometry, force_code, 'force')
            if not displayable_force_geometry:
                raise Exception, "Failed to create a displayable force geometry for %s" % force_name

            save_geos_polygons(force, displayable_force_geometry)


        if logger:
            # Finally, print and save the logged data about problems with the
            # datasets:
            date = datetime.datetime.today()
            date_string = datetime.datetime.strftime(date, '%Y-%m-%d_%H:%M:%S')
            commands_directory = os.path.dirname(os.path.realpath(__file__))
            save_path = os.path.normpath(os.path.join(commands_directory, '..', '..', '..', 'data', 'Police-debug-data-output_'+date_string))

            if not os.access(save_path, os.F_OK):
                os.mkdir(save_path)

            print ""
            print "----------------------------------------"
            print ""
            logger.print_and_save_logged_data(save_path)

