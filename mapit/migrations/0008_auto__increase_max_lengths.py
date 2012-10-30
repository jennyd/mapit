# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Code.code'
        db.alter_column('mapit_code', 'code', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Changing field 'NameType.code'
        db.alter_column('mapit_nametype', 'code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100))

        # Changing field 'NameType.description'
        db.alter_column('mapit_nametype', 'description', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'CodeType.code'
        db.alter_column('mapit_codetype', 'code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100))

        # Changing field 'CodeType.description'
        db.alter_column('mapit_codetype', 'description', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Postcode.postcode'
        db.alter_column('mapit_postcode', 'postcode', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100))

        # Changing field 'Country.code'
        db.alter_column('mapit_country', 'code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100))

        # Changing field 'Country.name'
        db.alter_column('mapit_country', 'name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255))

        # Changing field 'Type.code'
        db.alter_column('mapit_type', 'code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100))

        # Changing field 'Type.description'
        db.alter_column('mapit_type', 'description', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Area.name'
        db.alter_column('mapit_area', 'name', self.gf('django.db.models.fields.CharField')(max_length=255))

        # Changing field 'Name.name'
        db.alter_column('mapit_name', 'name', self.gf('django.db.models.fields.CharField')(max_length=255))

    def backwards(self, orm):

        # Changing field 'Code.code'
        db.alter_column('mapit_code', 'code', self.gf('django.db.models.fields.CharField')(max_length=10))

        # Changing field 'NameType.code'
        db.alter_column('mapit_nametype', 'code', self.gf('django.db.models.fields.CharField')(max_length=10, unique=True))

        # Changing field 'NameType.description'
        db.alter_column('mapit_nametype', 'description', self.gf('django.db.models.fields.CharField')(max_length=200))

        # Changing field 'CodeType.code'
        db.alter_column('mapit_codetype', 'code', self.gf('django.db.models.fields.CharField')(max_length=10, unique=True))

        # Changing field 'CodeType.description'
        db.alter_column('mapit_codetype', 'description', self.gf('django.db.models.fields.CharField')(max_length=200))

        # Changing field 'Postcode.postcode'
        db.alter_column('mapit_postcode', 'postcode', self.gf('django.db.models.fields.CharField')(max_length=7, unique=True))

        # Changing field 'Country.code'
        db.alter_column('mapit_country', 'code', self.gf('django.db.models.fields.CharField')(max_length=1, unique=True))

        # Changing field 'Country.name'
        db.alter_column('mapit_country', 'name', self.gf('django.db.models.fields.CharField')(max_length=100, unique=True))

        # Changing field 'Type.code'
        db.alter_column('mapit_type', 'code', self.gf('django.db.models.fields.CharField')(max_length=3, unique=True))

        # Changing field 'Type.description'
        db.alter_column('mapit_type', 'description', self.gf('django.db.models.fields.CharField')(max_length=200))

        # Changing field 'Area.name'
        db.alter_column('mapit_area', 'name', self.gf('django.db.models.fields.CharField')(max_length=100))

        # Changing field 'Name.name'
        db.alter_column('mapit_name', 'name', self.gf('django.db.models.fields.CharField')(max_length=100))

    models = {
        'mapit.area': {
            'Meta': {'ordering': "('name', 'type')", 'object_name': 'Area'},
            'country': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'areas'", 'null': 'True', 'to': "orm['mapit.Country']"}),
            'generation_high': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'final_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'generation_low': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'new_areas'", 'null': 'True', 'to': "orm['mapit.Generation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'parent_area': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['mapit.Area']"}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'areas'", 'to': "orm['mapit.Type']"})
        },
        'mapit.code': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Code'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.Area']"}),
            'code': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'codes'", 'to': "orm['mapit.CodeType']"})
        },
        'mapit.codetype': {
            'Meta': {'object_name': 'CodeType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.country': {
            'Meta': {'object_name': 'Country'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        'mapit.generation': {
            'Meta': {'object_name': 'Generation'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.geometry': {
            'Meta': {'object_name': 'Geometry'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'polygons'", 'symmetrical': 'False', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'polygon': ('django.contrib.gis.db.models.fields.PolygonField', [], {'srid': '27700'})
        },
        'mapit.name': {
            'Meta': {'unique_together': "(('area', 'type'),)", 'object_name': 'Name'},
            'area': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'names'", 'to': "orm['mapit.NameType']"})
        },
        'mapit.nametype': {
            'Meta': {'object_name': 'NameType'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'mapit.postcode': {
            'Meta': {'ordering': "('postcode',)", 'object_name': 'Postcode'},
            'areas': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'postcodes'", 'blank': 'True', 'to': "orm['mapit.Area']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True'}),
            'postcode': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'})
        },
        'mapit.type': {
            'Meta': {'object_name': 'Type'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'description': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['mapit']