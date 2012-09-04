# This script is used after Boundary-Line has been imported to create police
# force areas in England and Wales from the other administrative areas which
# they cover.

import os

from optparse import make_option

from django.core.management.base import NoArgsCommand

from mapit.models import Area, Geometry, Generation, Country, Type, CodeType, NameType
from mapit_UK_police_areas_england_wales import police_areas


class Command(NoArgsCommand):
    help = 'Create police force areas from existing Boundary-Line areas'
    option_list = NoArgsCommand.option_list + (
        make_option(
            '--commit',
            action='store_true',
            dest='commit',
            help='Actually update the database'
        ),
    )

    def handle_noargs(self, **options):
        current_generation = Generation.objects.current()
        new_generation = Generation.objects.new()
        if not new_generation:
            raise Exception, "No new generation to be used for import!"

        force_type_code = 'POF'
        force_area_type = Type.objects.get(code=force_type_code)

        name_type = NameType.objects.get(code='P')
        code_type = CodeType.objects.get(code='police_id')

        england = Country.objects.get(code='E')
        wales = Country.objects.get(code='W')

        welsh_forces = ('dyfed-powys', 'gwent', 'north-wales', 'south-wales')

        if not options['commit']:
            print "(not saving changes as --commit not specified)"

        for police_area in police_areas:
            force_code = police_area['code']
            force_name = police_area['name']
            country = wales if (force_code in welsh_forces) else england

            try:
                force = Area.objects.get(codes__code=force_code,
                                         type=force_area_type)
                print "Area matched: %s" % force
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
                force.save()
                force.names.update_or_create({ 'type': name_type },
                                             { 'name': force_name })
                force.codes.update_or_create({ 'type': code_type },
                                             { 'code': force_code })
                force.polygons.clear()

            print "  This force area covers:"
            # For the Metropolitan Police Service, add all the London boroughs
            # except the City of London, to avoid having to list every borough
            # in police_areas:
            if force_code == 'metropolitan':
                boroughs = Area.objects.filter(type__code="LBO").exclude(names__name__contains="City of London")
                for b in boroughs:
                    print "   ", b
                if boroughs.count() != 32:
                    raise Exception, "There should be 32 London boroughs for the Metropolitan Police area, but there are %d" % boroughs.count()
                if options['commit']:
                    force.polygons.add(*Geometry.objects.filter(areas__in=boroughs))
                continue

            # For all other forces, look for an Area matching each named area in
            # the descriptions, and add their polygons to the force's polygons:
            for a in police_area['lookup']:
                lookup_type_code, lookup_name = a
                try:
                    area = Area.objects.get(type__code=lookup_type_code,
                                            names__name__contains=lookup_name)
                    print "   ", area
                except Area.DoesNotExist:
                    raise Exception, "Area matching %s not found" % str(a)
                except Area.MultipleObjectsReturned:
                    print "More than one area found matching", a
                    for match in Area.objects.filter(
                                        type__code=lookup_type_code,
                                        names__name__contains=lookup_name):
                        print " ", match
                    raise Exception, "More than one area found matching %s" % str(a)
                if options['commit']:
                    force.polygons.add(*area.polygons.all())

