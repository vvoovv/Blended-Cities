##@mainpage Blended Cities internal documentation
# v0.6 for Blender 2.5.8a
#
# this is the continuation of a project begun with 2.4x releases of blender :
#
# http://jerome.le.chat.free.fr/index.php/en/city-engine
#
# the version number starts after the last blended cities release for 2.49b \
# but this is tests stage for now (july 2011)

##@file
# main.py
# the main city class
# bpy.context.scene.city
# the file calls the other modules and holds the main city methods

# class_import is responsible for loading the builders classes and guis from the builder folder
# this id done now before the city main class to register
# in order to give pointers towards builders to the main class


import sys
import copy
import collections

import bpy
import blf
import mathutils
from mathutils import *

#from blended_cities.core.ui import *
#from blended_cities.core.class_import import *
from blended_cities.core.class_main import *
from blended_cities.utils.meshes_io import *


## should be the system from script events with logger popup etc.
def dprint(str,level=1) :
    city = bpy.context.scene.city
    if level <= city.debuglevel :
        print(str)


## return the active builder classes as a list
# @return [ [class name1, class1], [class name2, class2], ... ]
def builderClass() :
    scene = bpy.context.scene
    city = scene.city
    buildersList = []
    for k in city.builders.keys() :
        if type(city.builders[k]) == list :
            dprint('found builder %s'%(k),2)
            builderCollection = eval('city.builders.%s'%k)
            buildersList.append([k,builderCollection])
    return buildersList


## bpy.context.scene.city
# main class, main methods. holds all the pointers to element collections
class BlendedCities(bpy.types.PropertyGroup) :
    elements = bpy.props.CollectionProperty(type=BC_elements)
    outlines = bpy.props.CollectionProperty(type=BC_outlines)
    #builders = BC_builders
    debuglevel = bpy.props.IntProperty(default=1)
    builders_info = {} # info about builder authoring, should be a collection too. usage, could use bl_info..

    bc_go = bpy.props.BoolProperty()
    bc_go_once = bpy.props.BoolProperty()


    ## create several elements in a row
    # @param what a list of object or the keyword 'selected'
    # @builder the name of the builder class
    # @otl_ob True if the outline object already exists. example for stack, the otl object is generated by elementStack from its parent
    # @build True True if one want the builder object to be built right now
    # @return a list of [ bld, otl ] for each builded object (the new element in its class, and its outline)
    def elementAdd(self,what='selected',builder='buildings', otl_ob=True, build=True) :
        # lists of outlines object given by user selection
        if what == 'selected' :
            otl_objects = bpy.context.selected_objects
        elif what :
            otl_objects = what # defined list of objects (from elementStack for ex.)
        else :
            otl_objects = ['none']
            otl_ob = False
        # the outline object is not known yet. no build() then
        #if otl_ob == False : build = False
        new_elms = []
        for otl_object in otl_objects :

            if otl_object == 'none' or type(otl_object.data) == bpy.types.Mesh :

                dprint('** element add')
                elementName = builder
                #dprint('ischild : %s'%(isChild))
                # check if the class exist
                try : elmclass = eval('self.builders.%s'%builder)
                except :
                    dprint('class %s not found.'%builder)
                    return False, False

                
                # create a new outline as element 
                otl_elm = self.elements.add()
                otl_elm.nameNew('outlines')
                otl_elm.type = 'outlines'
                # a new outline in its class
                otl = self.outlines.add()
                otl.name = otl_elm.name
                otl.type = builder

                if otl_ob :
                    otl_elm.pointer = str(otl_object.as_pointer())
                    otl.dataRead()
                else : otl_elm.pointer = '-1'  # todo : spawn a primitive of the elm class

                # the new object as element
                new_elm = self.elements.add()
                new_elm.nameNew(elementName)
                new_elm.type = builder

                # and in its class
                new  = elmclass.add()
                new.name  = new_elm.name

                # link the new elm and the new outline
                new.attached  = otl.name
                otl.attached = new.name

                # link parent and child
                # don't build if child element, the caller function will handle that, 
                # depending on other factors (object parenting ? build above existing ? deform outline ? etc)
                # it depends on the builder methods and where the caller want to locate the child 
                if otl_ob :
                    new.build()
                dprint('* element add done')
                new_elms.append([new, otl])
        return new_elms


    ## stack several new elements on different outlines in a row
    # @param what a list of object or the keyword 'selected'
    # @builder the name of the builder class
    # @return a list of [ bld, otl ] for each builded object (the new element in its class, and its outline)
    def elementStack(self,what='selected',builder='buildings'):
        if what == 'selected' :
            parent_objects = bpy.context.selected_objects
        else :
            otl_objects = what
        new_elms = []
        for object in parent_objects :
            if type(object.data) == bpy.types.Mesh :
                bld_parent, otl_parent = self.elementGet(object)
                print('stacking over %s'%bld_parent.name)
                bld_child, otl_child = bld_parent.stack(builder)
                new_elms.append([bld_child, otl_child])
        return new_elms

    # in [list of objects], remove builder x
    ## remove an existing element given an object or an element of any kind
    # will only let the outline object
    def elementRemove(self,what='selected',builder='none',remove_element=True):
        dprint('** REMOVE : %s %s'%(what,builder))
        if what == 'selected' :
            objects = bpy.context.selected_objects
        elif what == 'all' :
            objects = bpy.context.scene.objects
        else :
            objects = what
        del_objs = []
        for object in objects :
            print(object,type(object))
            if type(object.data) == bpy.types.Mesh :
                bld, otl = self.elementGet(object)
                if bld :
                    del_objs.append(object.name)
                    if remove_element :
                        dprint('. removing ob %s and its element'%(object.name))
                        bld.remove()
                    else :
                        dprint('. removing ob %s')
                        bld.objectRemove()

        return del_objs

    ## given an object or its name, returns the builder and the outline
    # @return [ bld, otl ] (the new element in its class, and its outline). [False,False] if not an element. [None,None] if not exist
    def elementGet(self,ob=False) :
        if ob == False :
            ob = bpy.context.active_object
        # given an object or its name, returns a city element (in its class)
        if type(ob) == str :
            try : ob = bpy.data.objects[ob]
            except :
                dprint('object with name %s not found'%ob)
                return [None,None]
        pointer = str(ob.as_pointer())
        for elm in self.elements :
            if elm.pointer == pointer :
                return [elm.asBuilder(),elm.asOutline()]
        return [False,False]


    ## modal configuration of script events
    def modalConfig(self) :
        mdl = bpy.context.window_manager.modal
        mdl.func = 'bpy.context.scene.city.modal(self,context,event)'


    ## the HUD function called from script events (TO DO)
    def hud() :
        pass


    ## the modal function called from script events (TO DO)
    def modal(self,self_mdl,context,event) :
            dprint('modal')
            if bpy.context.mode == 'OBJECT' and \
            len(bpy.context.selected_objects) == 1 and \
            type(bpy.context.active_object.data) == bpy.types.Mesh :
                elm,otl = self.elementGet(bpy.context.active_object)
                if elm : elm.build(True)
            '''
                if elm.className() == 'buildings' or elm.peer().className() == 'buildings' :
                    dprint('rebuild')
                    if elm.className() == 'buildings' :
                        blg = elm
                    else :
                        blg = elm.peer()
                    dprint('rebuild')
                    blg.build(True)

            if event.type in ['TAB','SPACE'] :
                self.go_once = True

            if event.type in ['G','S','R'] :
                self.go=False
                
                if bpy.context.mode == 'OBJECT' and \
                len(bpy.context.selected_objects) == 1 and \
                type(bpy.context.active_object.data) == bpy.types.Mesh :
                    elm = self.elementGet(bpy.context.active_object)
                    if elm : self.go=True

            elif event.type in ['ESC','LEFTMOUSE','RIGHTMOUSE'] :
                    self.go=False
                    self.go_once=False
                    #dprint('modal paused.')
                    #mdl.log = 'paused.'
                    #context.region.callback_remove(self._handle)

            if event.type == 'TIMER' and (self.go or self.go_once) :
                        #self_mdl.log = 'updating...'

                        #dprint('event %s'%(event.type))
                        elm = self.elementGet(bpy.context.active_object)
                        #dprint('modal acting')

                        if elm.className() == 'buildings' or elm.peer().className() == 'buildings' :
                            if elm.className() == 'buildings' :
                                blg = elm
                            else :
                                blg = elm.peer()
                            dprint('rebuild')
                            blg.build(True)
            #bpy.ops.object.select_name(name=self.name)
                        self.go_once = False
                        #if self.go == False : mdl.log = 'paused.'
            '''


    ## clean everything, restore the defaults
    # configure also the modal (it won't if BC is enabled by default, for now must be started by hand with city.modalConfig() )
    def init(self) :
        #
        #city = bpy.data.scenes[0].city
        city = self
        # clean elements collections
        while len(city.elements) > 0 :
            city.elements.remove(0)
        while len(city.outlines) > 0 :
            city.outlines.remove(0)
        for buildname, buildclass in builderClass() :
            while len(buildclass) > 0 :
                buildclass.remove(0)

        # define default value
        city.modalConfig()
        bpy.context.scene.unit_settings.system = 'METRIC'


    ## rebuild everything from the collections (TO COMPLETE)
    # should support criterias filters etc like list should also
    # @return [ bld, otl ] (the element in its class, and its outline).
    def build(self,what='all', builder='all') :
        objs = []
        dprint('\n** BUILD ALL\n')
        for buildnamse, buildclass in builderClass() :
            for elm in buildclass :
                dprint(elm.name)
                elm.build()
                objs.append([elm, elm.peer()])
        return objs

    ## list all or part of the elements, filters, etc.., show parented element
    # should be able to generate a selection of elm in the ui,
    # in a search panel (TO COMPLETE)
    def list(self,what='all', builder='all') :
        
        print('element list :\n--------------')
        def childsIter(otl,tab) :
            elm = otl.Child()
            while elm :
                ob = elm.asBuilder().object()
                obn = ob.name if ob else 'not built'
                print('%s%s : %s'%(tab,elm.asBuilder().name,obn))
                childsIter(elm,tab + '    ')
                elm = elm.Next()

        for otl in self.outlines :
            if otl.parent : continue
            ob = otl.asBuilder().object()
            obn = 'built' if ob else 'not built'
            print('%s : %s'%(otl.asBuilder().name,obn))
            childsIter(otl,'    ')

        print('collections check :\n-------')
        total = len(self.elements)
        print('%s elements :'%(total))
        print('outlines : %s'%(len(self.outlines)))
        count = len(self.outlines)
        bldclass = builderClass()
        for buildname,buildclass in bldclass :
            print('%s : %s'%(buildname,len(buildclass)))
            count += len(buildclass)
        if count != total : print("I've got a problem... %s / %s"%(count,total))


# register_class() for BC_builders and builders classes are made before
# the BlendedCities definition class_import
# else every module is register here
def register() :
    # operators
    pass

def unregister() :
    pass
if __name__ == "__main__" :
    dprint('B.C. wip')
    register()