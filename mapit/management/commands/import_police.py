# This script is used to import the boundaries of police neighbourhoods and
# forces in England and Wales into MaPit. It takes KML data from
# http://www.police.uk/data and JSON data from the Police API (which is fetched by fetch-police-api-data.py), so you need those first.

import HTMLParser
import json
import os
import re
import xml.sax
from xml.sax.handler import ContentHandler
from optparse import make_option
from django.core.management.base import BaseCommand
# Not using LayerMapping as want more control, but what it does is what this does
#from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import *
from mapit.models import Area, Geometry, Generation, Country, Type, CodeType, NameType
from utils import save_polygons


def parse_police_names_json(names_path):
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
        # print 'Parsing force names'
        force_names = json.load(f)
        names_dict = {}
        for force in force_names:
            # Strangely, the JSON seems to contain HTML entities, although only
            # for ampersands in neighbourhood names at the moment. HTMLParser
            # seems happy here too, though, so we may as well use it:
            force['name'] = h.unescape(force['name'])
            if force['id'] in names_dict:
                raise Exception, "Force id %s found twice in JSON" % force['id']
            names_dict[force['id']] = (force['name'], {})

    # For finding the maximum code and name lengths, to avoid having to change
    # fields again:
    code_max_length = 0
    name_max_length = 0

    for force_id in names_dict.keys():
        with open(os.path.join(names_path, force_id+'_neighbourhoods.json')) as f:
            print 'Parsing neighbourhood names in', force_id
            neighbourhood_names = json.load(f)
            for neighbourhood in neighbourhood_names:

                # Find the maximum code length:
                if len(neighbourhood['id']) > code_max_length:
                    code_max_length = len(neighbourhood['id'])
                # Find the maximum name length:
                if len(neighbourhood['name']) > name_max_length:
                    name_max_length = len(neighbourhood['name'])

                # As above, convert HTML entities:
                neighbourhood['name'] = h.unescape(neighbourhood['name'])
                if neighbourhood['id'] in names_dict[force_id][1]:
                    raise Exception, "Neighbourhood id %s found twice in force %s in JSON" % (neighbourhood['id'], force_id)
                names_dict[force_id][1][neighbourhood['id']] = neighbourhood['name']

    # print json.dumps(names_dict, indent=4)
    print 'code_max_length:', code_max_length
    print 'name_max_length:', name_max_length
    return names_dict


class Command(BaseCommand):
    help = 'Import KML data'
    args = '<Police neighbourhood KMLs, and Police API names JSON directories'
    # Should this have a --commit option? Not all other import scripts have it
    option_list = BaseCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        ),
    )

    def handle(self, kml_path, names_path, **options):

        # Move this out of handle()?
        def update_or_create_area():
            try:
                # Police neighbourhood codes are only guaranteed to be unique
                # within forces, not nationally, so parent_area is needed too.
                # type is probably unnecessary, but let's leave it in anyway:
                m = Area.objects.get(codes__code=code,
                                     type=area_type,
                                     parent_area=parent_area)
            except Area.DoesNotExist:
                m = Area(
                    name            = name,
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

            if area_type == neighbourhood_area_type:
                # Check that the feature is valid before transforming:
                geos_geometry = feat.geom.geos
                valid_before = geos_geometry.valid
                print '    Geometry valid before transforming:', valid_before
                if (not valid_before) and ('Self-intersection' not in feat.geom.geos.valid_reason):
                    raise Exception, 'Invalid geometry found before transforming, and not a self-intersection'

                g = feat.geom.transform(27700, clone=True)

                # Check that the feature is still valid after transforming:
                print '    Geometry valid after transforming:', g.geos.valid
#                if not g.geos.valid:
#                    raise Exception, 'Invalid geometry found after transforming'

                poly = [ g ]
            else:
                # Force area polygons are updated later from their children's
                # polygons:
                poly = None

            if options['commit']:
                m.save()
                m.names.update_or_create({ 'type': name_type }, { 'name': name })
                m.codes.update_or_create({ 'type': code_type }, { 'code': code })
                save_polygons({ m.id : (m, poly) })

                # Keep track of neighbourhood geometries which were invalid
                # before transforming:
                if area_type == neighbourhood_area_type and valid_before == False:
                    # raise Exception, 'Invalid geometry found before transforming'
                    # tuple of (number of points, area):
                    tup = (geos_geometry.num_coords, m)
                    print 'invalid_before.append():', tup
                    invalid_before.append(tup)
                    # This uses the area id as the key, whereas
                    # invalid_polygons_dict uses the geometry id as the key.
                    # This is probably confusing.
                    invalid_before_dict[m.id] = (force_code, neighbourhood_code)

            return m


        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"


        # names_path should contain an extra file for the names of all forces:
        if len(os.listdir(kml_path)) + 1 != len(os.listdir(names_path)):
            raise Exception, "The two datasets contain different numbers of forces!"


        names_dict = parse_police_names_json(names_path)

# FIXME check these against each other, but perhaps somewhere more sensible
#        neighbourhood_kmls_codes_set = set([])
#        neighbourhood_names_codes_set = set([])


        # These are for both forces and neighbourhoods:
        neighbourhood_area_type = Type.objects.get(code='PON')
        force_area_type = Type.objects.get(code='POF')

        england = Country.objects.get(code='E')
        wales = Country.objects.get(code='W')

        name_type = NameType.objects.get(code='P')
        code_type = CodeType.objects.get(code='police_id')

        # The police API doesn't provide this information:
        # (assuming that forces don't cross the border...)
        welsh_forces = ['dyfed-powys', 'gwent', 'north-wales', 'south-wales']


        # These store features which are invalid before transformation (directly
        # from the KML files). These will also be in invalid_polygons_dict,
        # since they will still be invalid when the polygons are created:

        # This stores tuples of (number of points, area object), to be sorted
        # to find the simplest one to try to fix:
        invalid_before = []
        # tup = (geos_geometry.num_coords, m)
        # invalid_before.append(tup)

        # This stores ids of neighbourhoods with polygons which were invalid
        # before transformation, with their force and neighbourhood codes, to
        # serialize to JSON and save at the end:
        invalid_before_dict = {}
        # invalid_before_dict[m.id] = (force_code, neighbourhood_code)

        # invalid_before_dict uses the area id as the key, whereas
        # invalid_polygons_dict uses the geometry id as the key.
        # This is probably confusing, and should be fixed.

        # This stores the geometry ids, and force and neighbourhood codes, of
        # any invalid neighbourhood polygons, which would cause the creation of
        # their force polygons via unionagg() to fail.
        invalid_polygons_dict = {}
        # invalid_polygons_dict[geometry.id] = (force_code, neighbourhood_code)

        # This stores ids of neighbourhoods, and their force and neighbourhood
        # codes, with missing names, to serialize to JSON and save at the end:
        missing_names_dict = {}
        # missing_names_dict[neighbourhood.id] = (force_code, neighbourhood_code)


        for force_code in os.listdir(kml_path):
            if force_code in names_dict.keys():
                force_name = names_dict[force_code][0]
            else:
                raise Exception, "Name for force %s not found" % force_code
                # print "Name for force %s not found, using code instead" % force_code
                # force_name = force_code
            print "Importing police force %s" % force_name

            if force_code in welsh_forces:
                country = wales
            else:
                country = england


            # Set these for update_or_create_area:
            area_type = force_area_type
            name = force_name
            code = force_code
            parent_area = None

            # Create the force, without any polygons for now:
            force = update_or_create_area()


            # Start dealing with neighbourhoods in this force:

            # parent_area needs to be set here, rather than using find_parents.py:
            parent_area = force
            area_type = neighbourhood_area_type
            force_directory = os.path.join(kml_path, force_code)
            for neighbourhood_kml in os.listdir(force_directory):
                neighbourhood_code = re.sub('\.kml$', '', neighbourhood_kml)
                if neighbourhood_code in names_dict[force_code][1].keys():
                    neighbourhood_name = names_dict[force_code][1][neighbourhood_code]
                    name_missing = False
                else:
                    # raise Exception, "Name for %s in %s not found" % (neighbourhood_code, force_name)
                    print "Name for %s in %s not found, using neighbourhood_code instead" % (neighbourhood_code, force_name)
                    neighbourhood_name = neighbourhood_code
                    name_missing = True
                print "  Importing neighbourhood %s from police force %s" % (neighbourhood_name, force_name)

                # Need to parse the KML manually to get the ExtendedData
                kml_data = KML()
                neighbourhood_kml = os.path.join(force_directory, neighbourhood_kml)
                xml.sax.parse(neighbourhood_kml, kml_data)

                ds = DataSource(neighbourhood_kml)
                layer = ds[0]
                # Assume only one feat in layer:
                if len(layer) > 1:
                    raise Exception, "More than one feature in layer for %s (%s)" % (neighbourhood_code, force_name)
                feat = layer[0]

                # Set these for update_or_create_area:
                name = neighbourhood_name
                code = neighbourhood_code


                neighbourhood = update_or_create_area()

                if name_missing == True:
                    missing_names_dict[neighbourhood.id] = (force_code, neighbourhood_code)

                # unionagg() fails when invalid polygons are included, so keep
                # track of them to exclude later:
                for geometry in neighbourhood.polygons.all():
                    if not geometry.polygon.valid:
#                        invalid_polygon_ids.append(geometry.id)
#                        invalid_polygons.append(geometry)

                        # This uses the geometry id as the key, whereas
                        # invalid_before_dict uses the area id as the key. This
                        # is probably confusing.
                        invalid_polygons_dict[geometry.id] = (force_code, neighbourhood_code)
                    else:
                        continue


            # Create a force area polygon from its neighbourhood children,
            # excluding invalid polygons:
            force_poly = Geometry.objects.filter(area__parent_area_id=force.id).exclude(id__in=invalid_polygons_dict.keys()).unionagg()
            print 'force_poly.valid:', force_poly.valid
            print 'force_poly.geom_type', force_poly.geom_type
            if options['commit']:
                # unionagg() gives us a nice polygon or multipolygon already, so
                # we can just save it directly without having to go through
                # save_polygons:
                if force_poly.geom_type == 'MultiPolygon':
                    force.polygons.all().delete()
                    for p in force_poly:
                        force.polygons.create(polygon=p)
                elif force_poly.geom_type == 'Polygon':
                    force.polygons.all().delete()
                    force.polygons.create(polygon=force_poly)
                else:
                    raise Exception, "force_poly for %s is neither a Polygon or a Multipolygon" % force.name
            else:
                print '(not trying to create force polygon(s) as --commit not specified)'


        # Finally, print and save helpful details about problems with the datasets:
        print '%d features invalid before transformation (see invalid_before.json)' % len(invalid_before)

        with open(os.path.join(save_path, 'invalid_before.json'), 'w') as f:
            print 'Saving invalid_before.json'
            json.dump(invalid_before_dict, f, indent=4)

        simplest = min(invalid_before)
        print 'Simplest polygon which was invalid before transformation:'
        print '  geometry.id:', simplest[1].id
        print '  parent area:', simplest[1].parent_area
        print '  neighbourhood codes:', simplest[1].codes.all()
        print '  number of points:', simplest[0]


        print "%d neighbourhood polygons are invalid and were excluded from their forces' polygons (see invalid_polygons.json)" % len(invalid_polygons_dict.keys())

        with open(os.path.join(save_path, 'invalid_polygons.json'), 'w') as f:
            print 'Saving invalid_polygons.json'
            json.dump(invalid_polygons_dict, f, indent=4)


        print 'Names were missing for %d neighbourhoods (see missing_names.json)' % len(missing_names_dict.keys())

        with open(os.path.join(save_path, 'missing_names.json'), 'w') as f:
            print 'Saving missing_names.json'
            json.dump(missing_names_dict, f, indent=4)


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

