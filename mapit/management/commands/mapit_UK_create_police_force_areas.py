# This script is used after Boundary-Line has been imported to create police
# force areas in England and Wales from the other administrative areas which
# they cover.
#
# This script takes JSON data from the Police API which is fetched by
# get-police-names.py, so run that first.

import HTMLParser
import json
import os

from optparse import make_option

from django.core.management.base import BaseCommand

# from django.contrib.gis.gdal import *
# from django.contrib.gis.geos import LinearRing, Polygon, MultiPolygon

from mapit.models import Area, Geometry, Generation, Country, Type, CodeType, NameType
from police_areas_england_wales import police_areas

def parse_police_names_json(names_path):

    """
    Parse the names data from the API JSON files, and return it in a dict.

    Return a dict mapping force code to force name.
    """

    h = HTMLParser.HTMLParser()
    names_dict = {}
    filename = 'forces.json'

    with open(os.path.join(names_path, filename)) as f:
        names = json.load(f)
    print "Parsing names from API data"
    for n in names:
        # Strangely, the JSON seems to contain HTML entities, so try to
        # unescape them:
        n['name'] = h.unescape(n['name'])
        if n['id'] in names_dict:
            raise Exception, "ID '%s' found twice in %s" % (n['id'], filename)
        names_dict[n['id']] = n['name']

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

def save_geos_polygons(area, geometry):

    """
    Save a geometry to an Area's polygons.

    Take an Area and a GEOSGeometry object, save the geometry (as one or more
    Geometry objects) to area.polygons, and return a list of tuples of
    Polygons and their Geometry IDs.
    """

    # This is similar to utils.save_polygons, but expects a GEOSGeometry
    # instead of an OGRGeometry.

    shapes = make_iterable_shapes(geometry)
    area.polygons.all().delete()
    for polygon in shapes:
        area.polygons.create(polygon=polygon.wkt)


class Command(BaseCommand):
    help = 'Create police force areas from existing Boundary-Line areas'
    args = '<names_path>'
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        ),
    )

    def handle(self, names_path, **options):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        force_type_code = 'PFL'
        force_area_type = Type.objects.get(code=force_type_code)

        name_type = NameType.objects.get(code='P')
        code_type = CodeType.objects.get(code='police_id')

        england = Country.objects.get(code='E')
        wales = Country.objects.get(code='W')

        welsh_forces = ('dyfed-powys', 'gwent', 'north-wales', 'south-wales')

        names_dict = parse_police_names_json(names_path)

        for police_area in police_areas:
            force_code = police_area[0]
            # Assume that the API data contains all force codes:
            force_name = names_dict[force_code]
            country = wales if (force_code in welsh_forces) else england

            try:
                force = Area.objects.get(codes__code=force_code,
                                         type=force_area_type)
                print "Area matched, %s" % force
            except Area.DoesNotExist:
                force = Area(
                    # If committing, name will be overwritten by the
                    # force.names.update_or_create:
                    name            = force_name,
                    type            = force_area_type,
                    country         = country,
                    generation_low  = new_generation,
                    generation_high = new_generation,
                )
                print "New area: %s %s" % (force_type_code, force_name)

            # check that we are not about to skip a generation
            if force.generation_high and current_generation and force.generation_high.id < current_generation.id:
                raise Exception, "Area %s found, but not in current generation %s" % (force_code, current_generation)

            force.generation_high = new_generation
            if options['commit']:
                print '  saving force'
                force.save()
                force.names.update_or_create({ 'type': name_type },
                                             { 'name': force_name })
                force.codes.update_or_create({ 'type': code_type },
                                             { 'code': force_code })

            # Create the Metropolitan Police Service area by unioning all the
            # London boroughs except the City of London, to avoid having to list
            # every borough in police_areas:
            if force_code == 'metropolitan':
                force_geom = Geometry.objects.filter(area__type__code="LBO").exclude(area__names__name__contains="City of London").unionagg()
            else:
                force_geom = None
                # For all other forces, look for an Area matching each named
                # area in the descriptions, and union their polygons to create a
                # geometry for the force area:
                lookup = police_area[1]['lookup']
                for a in lookup:
                    lookup_type_code, lookup_name = a
                    try:
                        area = Area.objects.get(type__code=lookup_type_code,
                                                names__name__contains=lookup_name)
                        area_unionagg = area.polygons.all().unionagg()
                        if force_geom:
                            old_area = force_geom.area
                            force_geom = force_geom.union(area_unionagg)
                        else:
                            old_area = 0
                            force_geom = area_unionagg
                        new_area = force_geom.area
                        if new_area <= old_area:
                            print "Force area not increased by adding the area found by lookup %s; has this area already been included by another lookup?" % str(a)
                    except Area.DoesNotExist:
                        print a, 'not found'
                    except Area.MultipleObjectsReturned:
                        print 'More than one area found matching', a
                        for match in Area.objects.filter(type__code=lookup_type_code,
                                                     names__name__contains=lookup_name):
                            print ' ', match
                        print '    No polygons from these areas were used.'
            if force_geom:
                print '  Geometry successfully created'
                if options['commit']:
                    save_geos_polygons(force, force_geom)
                else:
                    print '    (not saving geometry)'
            else:
                print '  No geometry created for', force_name

