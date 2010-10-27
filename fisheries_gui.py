#!/usr/bin/env python
"""Fisheries Economics Masterclass GUI"""

import wx
import wx.html
import fisheries_model
import colourblind

import matplotlib
#matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas
import numpy
import copy
import os
import sys

#String constants for some menus etc
MG_QUOTA='Output Controlled'
MG_EFFORT='Input Controlled'
SIM_DYNAMIC='Dynamic'
SIM_STATIC='Static (Equilibrium)'
#Version history:
#1.00 Initial release from Hobart Class 1
#1.01 Made fishery crash instantaneous. 
VERSIONSTRING = '1.01'

#Globals that specify the current simulation and management type
#(to be subsumed at a later stage...) 
SIM_TYPE=''
MG_TYPE=''


class Frame(wx.Frame):
    '''The main (only?) GUI Frame'''
    def __init__(self,width,height):
        wx.Frame.__init__(self,
                          None,
                          size=wx.Size(width,height),
                          title = 'Fisheries Explorer')
        #self.SetSize(wx.Size(width,height))
        #Set the starting simulation and management types
        global SIM_TYPE
        global MG_TYPE
        MG_TYPE = MG_QUOTA
        SIM_TYPE = SIM_STATIC
        self.Maximize()            
        #Initialise model components
        self._init_model()
        
        #Initialise model/graph update system
        self._init_update()

        #Initialise GUI components
        self._init_gui()
        

    def _init_update(self):
        '''Initialise model/graph update system'''
        
        #Will contain current parameters
        self.parameters= {}
        #Will contain last parameters for which the model run was completed
        self.computed_parameters = {}
        #Will contain last parameters for which a graph was produced
        self.plotted_parameters = {}
        
        #Whether current computation has been completed
        self.computed_complete = True
        
        #Timer for model reruns
        self.timer_model = wx.Timer(self)
        self.timer_model.Start(250)
        wx.EVT_TIMER(self,self.timer_model.GetId(),self.on_timer_model)
        #Hack to call layout after init
        self.timer_init_hack = wx.Timer(self)
        self.timer_init_hack.Start(250)
        wx.EVT_TIMER(self,self.timer_init_hack.GetId(),self.on_timer_init_hack)
        #The model execution thread
        self.model_thread = fisheries_model.MultiThreadModelRun(self.model_data_updater)
    
    def _init_model(self,type='catch'):
        '''Initialise model'''
        self.model = fisheries_model.lobsterModel(control_type = type)

    
    def _init_gui(self):
        '''Initialise GUI components'''
        
        #Setup sizers (in hierarchical order)
        self.sizer = wx.FlexGridSizer(rows=2,cols=1)

        #Create wx objects
        self.parameter_panel = ParameterPanel(self,self.model,sim_update_fx=self.on_simulation_change)
        self.plot_panel = PlotPanel(self)
        
        #Set up main sizer
        self.sizer.Add(self.parameter_panel,0,wx.EXPAND)
        self.sizer.Add(self.plot_panel,0,wx.EXPAND)
        self.sizer.AddGrowableCol(0,1)
        self.sizer.AddGrowableRow(1,1)
        
        #Set sizers
        self.SetSizer(self.sizer)
        
        #Set menu
        self.menubar = MenuBar(self,sim_update_fx=self.on_simulation_change,parameter_type_fx=self.parameter_panel.show_parameter_set,reset_model_fx=self.on_simulation_change)
        self.SetMenuBar(self.menubar)
        self.menubar.set_parameter_types(self.model.get_parameter_types())

        #Bind events
        self.Bind(wx.EVT_SCROLL,self.on_slide_change)

        #self.Bind(wx.EVT_CLOSE, self.onCloseWindow)
                
        self.on_slide_change(None)
        self.on_timer_model(None)
        
        #Prevent the frame getting resized too small
        min_size = self.sizer.GetMinSize()
        self.SetMinSize(min_size)
        
        
        #Set the icon
        self.icon = wx.Icon(os.path.join('images','fishnet.ico'),wx.BITMAP_TYPE_ICO)
        self.SetIcon(self.icon)

    #It still doesn't close cleanly for some unknown reason..
    block = False
    def onCloseWindow(self,event):
        self.timer_model.Stop()
        self.timer_model.Destroy()
        self.icon.Destroy()
        event.Skip()
        
        
    def on_timer_model(self,event):
        '''Rerun the model if parameters have changed'''
        #If parameters have changed we need to recalculate the model
        if self.parameters != self.computed_parameters:
            self.computed_complete=False
            self.model.set_parameters(self.parameter_panel.get_parameters())
            self.model.reset()
            
            #Run the appropriate simulation
            if SIM_TYPE == SIM_STATIC:
                if MG_TYPE == MG_QUOTA:
                    max= self.parameters['K']*self.parameters['r']/4*1.01
                    self.model_thread.run(self.model,20,dynamic=False,independent_variable='catch',independent_maximum=max)
                else:
                    self.model_thread.run(self.model,20,dynamic=False,independent_variable='effort',independent_maximum=6e6)
            else:
                self.model_thread.run(self.model,20)
            
            self.computed_parameters = self.parameters
 
    init_hack_count = 0
    def on_timer_init_hack(self,event):
        '''A hack to layout the plot panel after load. For some reason the legend is not displayed correctly.'''
        if self.init_hack_count > 0:
            self.timer_init_hack.Stop()
        self.init_hack_count += 1
        self.plot_panel.update_visibility()
        self.plot_panel.OnSize()
        self.plot_panel.Layout()
        
        
 
    def on_simulation_change(self,simulation_type,control_type):
        '''Called if the simulation type (static/dynamic, quota/effort controlled) changes'''
        global SIM_TYPE
        global MG_TYPE
        SIM_TYPE = simulation_type
        MG_TYPE = control_type
        
        #Initialise the model with appropriate control type
        if MG_TYPE == MG_QUOTA:
            self._init_model('catch')
        else:
            self._init_model('effort')
            
        self.computed_parameters = None
        self.parameter_panel.set_model(self.model)
        self.plot_panel.update_visibility()
        self.plot_panel.Layout()
        self.on_timer_model(None)

    def on_slide_change(self,event):
        '''Get the latest set of parameters if the sliders have been moved'''
        #Store the latest set of parameters
#        if event.GetEventObject() in self.parameter_panel.GetChildren():
        self.parameters = self.parameter_panel.get_parameters()
            
    def model_data_updater(self,state):
        self.computed_complete=True
        self.model.state = state
        self.plot_panel.update_state(self.model.state)
        min_size = self.sizer.GetMinSize()  
        self.SetMinSize(min_size)

        
                                  

class MenuBar(wx.MenuBar):
    def __init__(self,parent_frame,sim_update_fx=None,parameter_type_fx=None,reset_model_fx=None):
        wx.MenuBar.__init__(self)
        
        self.sim_update_fx = sim_update_fx
        self.parameter_type_fx=parameter_type_fx
        self.reset_model_fx = reset_model_fx
        self.parent_frame = parent_frame
        
        self.scenario_menu = wx.Menu()
        self.reset_model = self.scenario_menu.Append(-1,'Reset Model')
        self.scenario_menu.Append(-1,' ').Enable(False)        
        self.scenario_menu.AppendRadioItem(-1,'Rock Lobster Fishery')
        self.scenario_menu.Append(-1,' ').Enable(False)        
        self.static_simulation = self.scenario_menu.AppendRadioItem(-1,SIM_STATIC)
        self.dynamic_simulation = self.scenario_menu.AppendRadioItem(-1,SIM_DYNAMIC)
        self.scenario_menu.Append(-1,' ').Enable(False)        
        self.input_control = self.scenario_menu.AppendRadioItem(-1,MG_EFFORT)
        self.output_control = self.scenario_menu.AppendRadioItem(-1,MG_QUOTA)
        
        #Bring checks in line with initial simulation state
        if SIM_TYPE == SIM_STATIC:
            self.static_simulation.Check()
        else:
            self.dynamic_simulation.Check()
        if MG_TYPE == MG_QUOTA:
            self.output_control.Check()
        else:
            self.input_control.Check()
        
        
        self.parameter_menu = wx.Menu()
        self.parameter_items = []

        self.help_menu = wx.Menu()
        self.about = self.help_menu.Append(-1,'About')
        self.license = self.help_menu.Append(-1,'License')
        
        self.Append(self.scenario_menu,'Model')
        self.Append(self.parameter_menu,'Parameters')
        self.Append(self.help_menu,'Help')
        
        parent_frame.Bind(wx.EVT_MENU, self.on_simulation_change, self.input_control)
        parent_frame.Bind(wx.EVT_MENU, self.on_simulation_change, self.output_control)
        parent_frame.Bind(wx.EVT_MENU, self.on_simulation_change, self.static_simulation)
        parent_frame.Bind(wx.EVT_MENU, self.on_simulation_change, self.dynamic_simulation)
        parent_frame.Bind(wx.EVT_MENU, self.on_about,self.about)
        parent_frame.Bind(wx.EVT_MENU, self.on_license,self.license)
        parent_frame.Bind(wx.EVT_MENU, self.on_simulation_change, self.reset_model)
    
    def set_parameter_types(self,types):
        for item in self.parameter_items:
            self.parameter_menu.Delete(item)
        
        for type in ["All"]+types:
            self.parameter_items.append(self.parameter_menu.AppendRadioItem(-1,type))
            self.parent_frame.Bind(wx.EVT_MENU, self.on_parameter_selection,
                                   self.parameter_items[-1])
            if type == 'Management Controls':
                self.parameter_items[-1].Check()

        self.on_parameter_selection(None)
        
    def on_reset_model(self,event):
        '''Reset the model'''
        self.reset_model_fx()

    def on_parameter_selection(self,event):
        '''Called when a parameter set is selected'''
        for item in self.parameter_items:
            if item.IsChecked():
                self.parameter_type_fx(item.GetText())
                       
        
    def on_simulation_change(self,event):
        if self.input_control.IsChecked():
            control_type = MG_EFFORT
        else:
            control_type = MG_QUOTA
        
        if self.static_simulation.IsChecked():
            simulation_type = SIM_STATIC
        else:
            simulation_type= SIM_DYNAMIC
        self.sim_update_fx(simulation_type = simulation_type, control_type = control_type)
        event.Skip()
        
           
    def on_about(self,event):
        '''About handler, shows modal AboutBox'''
        dlg = AboutBox(self.parent_frame,title='About Fisheries Explorer',filename='about.html')
        dlg.ShowModal()
        dlg.Destroy()
                
    def on_license(self,event):
        '''License handler, shows modal AboutBox'''
        dlg = AboutBox(self.parent_frame,title='Fisheries Explorer License',filename='license.html')
        dlg.ShowModal()
        dlg.Destroy()
                

class ParameterPanel(wx.Panel):
    '''A panel for parameter input'''
    def __init__(self,parent,model = [],sim_update_fx=None):
        wx.Panel.__init__(self,parent)
        self.type_shown = 'All'
        self.model = model
        self.parameters = model.get_parameters()
        self._base_layout()
        self.set_model(model)
        self.sim_update_fx = sim_update_fx
    
    def set_model(self,model):
        '''Set the parameters displayed in the panel (expects a Parameter object)'''
        self.parameters = model.get_parameters()
        self.model = model
        self.parameter_layout()    
        self.show_parameter_set()

    def _base_layout(self):
        
        #Empty lists for storing gui objects (to get parameter values etc)
        self.label_parameters = {}
        self.label_param_values = {}
        self.slider_parameters = {}            

        self.sizer = wx.FlexGridSizer(rows=1,cols=2)
        self.sizer.AddGrowableCol(1,1)
        self.SetSizer(self.sizer)
        
        self.set_panel = wx.Panel(self)
        self.set_sizer = wx.FlexGridSizer(rows=3,cols=1)
        self.set_panel.SetSizer(self.set_sizer)
        
        self.control_panel = wx.Panel(self)
        self.control_sizer = wx.FlexGridSizer(rows=len(self.parameters),cols=3)
        self.control_sizer.AddGrowableCol(1,1)
        self.control_panel.SetSizer(self.control_sizer)

        self.sizer.Add(self.set_panel,0)
        self.sizer.Add(self.control_panel,0,flag=wx.EXPAND)

        if False:
            #Drop down box for choosing parameter types
            self.set_sizer.Add(wx.StaticText(self.set_panel,label='Parameter Set:'))
            self.parameter_choice = wx.Choice(self.set_panel,1)
            self.set_sizer.Add(self.parameter_choice)
            #Set selection items
            items = self.model.get_parameter_types()
            items.insert(0,'ALL')
            self.parameter_choice.SetItems(items)
            self.parameter_choice.SetSelection(0)
        if False:
            self.static_toggle = wx.RadioBox(self.set_panel,1,"Simulation Type",choices=[SIM_STATIC,SIM_DYNAMIC])
            self.management_toggle = wx.RadioBox(self.set_panel,1,"Management Type",choices=[MG_EFFORT,MG_QUOTA])
            self.set_sizer.Add(self.static_toggle)
            self.set_sizer.Add(self.management_toggle)
        
        self.Bind(wx.EVT_CHOICE,self.on_selection_change)
        self.Bind(wx.EVT_RADIOBOX,self.on_simulation_change)
        
        
    def parameter_layout(self):

        #Delete all existing objects
        if hasattr(self,'control_sizer'):
            self.control_sizer.Clear(True)

        #Create the caption, value and slider for each parameter
        count = 0
        for param in self.parameters:
            p = self.parameters[param]
            self.label_parameters[param]=wx.StaticText(self.control_panel,label=p['title']+':')
            current_value = round((p['value']-p['min'])/float(p['max']-p['min'])*1000)
            self.slider_parameters[param]= wx.Slider(self.control_panel, -1, current_value, 0, 1000, wx.DefaultPosition, 
                                                     style= wx.SL_HORIZONTAL)
            self.label_param_values[param]=wx.StaticText(self.control_panel,label='')
            self.label_parameters[param].SetToolTipString(p['description'])
            self.slider_parameters[param].SetToolTipString(p['description'])

            self.control_sizer.Add(self.label_parameters[param],0,flag=wx.ALIGN_BOTTOM | wx.ALIGN_RIGHT)
            self.control_sizer.Add(self.slider_parameters[param],0,flag=wx.EXPAND)
            self.control_sizer.Add(self.label_param_values[param],0,flag=wx.ALIGN_LEFT)
            count += 1
        self.on_slide_change(None)
            
        self.Bind(wx.EVT_SCROLL,self.on_slide_change)

    
    def on_simulation_change(self,event):
        self.sim_update_fx(simulation_type = self.static_toggle.GetStringSelection(),
                           control_type = self.management_toggle.GetStringSelection())
    
    def on_selection_change(self,event):
        '''Update parameter list when a different parameter set is selected'''
        type = self.parameter_choice.GetItems()[self.parameter_choice.GetSelection()]
        self.show_parameter_set(type)
        
    def show_parameter_set(self,type=None):
        '''Show parameters of type'''
        
        #If type is unspecified we show the same parameter set
        if type != None:
            self.type_shown = type
        type = self.type_shown

        #Show the selected parameters
        for param in self.parameters:
            selected =((type == 'ALL' or 
                        type == 'All' or 
                        self.parameters[param]['type'] == type)
                        and (SIM_TYPE == SIM_DYNAMIC or self.parameters[param]['type'] != 'Management Controls'))  
            if SIM_TYPE == SIM_STATIC and param == 'discount_rate':
                selected = False
            self.label_param_values[param].Show(selected)
            self.label_parameters[param].Show(selected)
            self.slider_parameters[param].Show(selected)
        self.Fit()
        self.GetParent().Layout()
        
    def on_slide_change(self,event):
        '''Slider change event updates value label'''
        param_values = self.get_parameters()
        for param in (param_values):
            scale_text = ''
            if self.parameters[param]['scale_text'] != '':
                scale_text = ' (' + self.parameters[param]['scale_text'] + ')'
            self.label_param_values[param].SetLabel(str(param_values[param]/self.parameters[param]['scale'])+  ' ' + self.parameters[param]['units'] + scale_text)
        self.Layout()
        #Propagate the event so that the frame can process it
        if event != None:
            event.Skip()

    def get_parameters(self):
        '''Get a dict of the current parameter values'''
        out = {}
        for param in self.parameters:
            p = self.parameters[param]
            out[param] = float(self.slider_parameters[param].GetValue())/1000.0*(p['max']-p['min'])+p['min']
        
        return out
    
    def set_parameters(self,parameter_values):
        '''Update parameters from a dict'''
        out = {}
        for param in parameter_values.keys():
            if self.parameters.has_key(param):
                v = parameter_values[param]
                p = self.parameters[param]
                self.slider_parameters[param].SetValue(int((v-p['min'])/(p['max']-p['min'])*1000))
        self.on_slide_change(None)
         
class PlotPanel(wx.Panel):
    
    line_colours = colourblind.rgbScaled
    line_styles = [[127,1],         #solid
                   [5,5],           #dashed
                   [20,20,2,20],       #dash-dot
                   [2,2,2,2]        #dotted
                   ]
    
    
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)


        self.last_redraw_size = []

        self.fig = Figure()
        self.fig.set_facecolor([1,1,1])
        
        self.control_panel = wx.Panel(self)
        self.canvas_panel = wx.Panel(self)
        self.canvas = FigCanvas(self.canvas_panel,wx.ID_ANY,self.fig)
        
        
        self.sizer = wx.FlexGridSizer(rows=1,cols=2,hgap=5,vgap=5)
        self.sizer.Add(self.canvas_panel,flag=wx.EXPAND)
        self.sizer.Add(self.control_panel,flag=wx.ALIGN_CENTER|wx.ALL)
        self.sizer.AddGrowableCol(0,1)
        self.sizer.AddGrowableRow(0,1)

        self.SetSizer(self.sizer)
        
        self.control_sizer = wx.FlexGridSizer(hgap=5,vgap=5)
        self.control_panel.SetSizer(self.control_sizer)
        self.control_panel.Bind(wx.EVT_CHECKBOX,self.redraw)
        
#        self.canvas.SetAutoLayout(True)
        self.canvas_panel.SetMinSize([600,300])
        self.state = None
        self.bounds = {}
        self.xbound = 0
        self.SetBackgroundColour(wx.WHITE)
        self.canvas_panel.SetBackgroundColour(wx.WHITE)
        self.control_panel.SetBackgroundColour(wx.WHITE)    
        self.canvas_panel.Bind(wx.EVT_SIZE, self.OnSize)
        self.Fit()
    
    def OnSize(self,event=None,size=None):
        
        if event == None and size == None:
            size = self.canvas_panel.GetClientSize()
        elif event != None and size == None:
            size = event.GetSize()
        #If the size has actually changed we redraw (several events may 
        #be intercepted here per resize)
        if size != self.last_redraw_size:
            self.last_redraw_size = size
            self.fig.set_figwidth(size[0]/(1.0*self.fig.get_dpi()))
            self.fig.set_figheight(size[1]/(1.0*self.fig.get_dpi()))
            self.canvas.SetClientSize(size)
            self.redraw(None, redraw=True)
        
        
        if event != None:
            event.Skip()         
        

    def _setup_control_panel(self):
        self._update_line_styles()
        
        #Remove existing widgets
        self.control_sizer.Clear(True)
        
 
        parameters = self.state.attribute_order

        self.control_sizer.SetRows(len(parameters))
        self.control_sizer.SetCols(3)

       #Column Labels
        if False:
            self.control_sizer.SetRows(len(parameters)+1)
            column_labels = ['Plot','Parameter','Style']
            for col in range(len(column_labels)):
                self.control_sizer.Add(wx.StaticText(self.control_panel,-1,column_labels[col]))
            
        self.check_boxes = {}
        self.param_text = {}
        self.param_bitmap = {}
        self.pens = {}
        self.colours = {}
        self.linedc = {}
        self.linebitmap = {}
#        self.check_boxes = {}
        linedc = wx.MemoryDC()
        for param in parameters:
            rgbcolour = self.unit_colour[self.state.get_attribute_units(param)]
            self.colours[param] = wx.Colour(rgbcolour[0]*255,rgbcolour[1]*255,rgbcolour[2]*255)
            style = self.parameter_style[param]

            #Add the check box
            self.check_boxes[param] = wx.CheckBox(self.control_panel,-1,'')
            self.control_sizer.Add(self.check_boxes[param])
            
            #Add the description
            self.param_text[param] = wx.StaticText(self.control_panel,-1,self.state.get_attribute_title(param)) 
            self.control_sizer.Add(self.param_text[param])
            self.param_text[param].SetForegroundColour(self.colours[param])
            self.param_text[param].Refresh()
            
            #Add the linestyle
            self.linebitmap[param] = wx.EmptyBitmap(40,20)
            linedc.SelectObject(self.linebitmap[param])
            linedc.Clear()
            self.pens[param] = wx.Pen(colour = self.colours[param], width = 1,style = wx.USER_DASH)
            self.pens[param].SetDashes(style)
            linedc.SetPen(self.pens[param])
            linedc.DrawLine(0,10,40,10)
            self.param_bitmap[param] = wx.StaticBitmap(self.control_panel,-1,self.linebitmap[param])
            self.control_sizer.Add(self.param_bitmap[param])

        #Enable the default plot parameters
        for param in self.state.default_plot:
            self.check_boxes[param].SetValue(True)
        
        


    def _colour_control(self):
        '''
        updates the colours of the control elements
        '''
        selected = self.get_selected_parameters()
        for param in self.state.attributes:
            if param in selected:
                self.param_text[param].Enable()
                self.param_bitmap[param].Enable()
            else:
                self.param_text[param].Disable()
                #self.param_bitmap[param].Disable()
        

            
    def _update_line_styles(self):
        '''
        Update the colour and style associated with each unit and parameter
        ''' 
        self.unit_colour = {}
        self.parameter_style = {}
        
        #For tracking the number of parameters per unit
        unit_count = {}
        
        #Determine colours for units
        for unit in self.state.unit_order:
            self.unit_colour[unit] = self.line_colours[len(self.unit_colour)]
            unit_count[unit] = 0
            
        #Determine line styles for parameters
        for param in self.state.attribute_order:
            unit = self.state.get_attribute_units(param)
            print param, unit
            self.parameter_style[param] = self.line_styles[unit_count[unit]]
            unit_count[unit] += 1

    def _select_parameters(self,parameters = [],redraw=True):
        '''Set the parameters to be plotted'''
        self.parameters = parameters
        if redraw: 
            self.redraw_fromscratch()
        
    def update_visibility(self):
        if SIM_TYPE == SIM_STATIC:
            enabled = False
        else:
            enabled = True
        self.check_boxes['discounted_profit'].Show(enabled)
        self.param_text['discounted_profit'].Show(enabled)
        self.param_bitmap['discounted_profit'].Show(enabled)
        
    def update_state(self,state,redraw=True):
        '''Update the state that is being plotted'''
        self.state = copy.deepcopy(state)
        if not hasattr(self,'last_parameters'):
            self.last_parameters = {}
            
        print self.state['discounted_profit']
        import numpy
        self.npv = numpy.nansum(self.state['discounted_profit'])
#        discount_rate = 0.05
        
#        for index in range(len(self.state['revenue'])):
#            if self.state['revenue'][index] != None and ~numpy.isnan(self.state['revenue'][index]):
#                self.npv += (self.state['revenue'][index]-self.state['cost'][index])*(1-discount_rate)**index
             
        if redraw:
            #Update the parameter selection controls if necessary
            if state.attributes != self.last_parameters:
                self._setup_control_panel()
                self.last_parameters = state.attributes
            self.redraw()

    def _update_bounds(self):
        '''Update the figure bounds'''

            
        def sig_round(number):
            '''Ceil a number to a nice round figure for limits'''
            if number == 0:
                return 0
            sig = number/(10**numpy.floor(numpy.log10(number*2)))
            
            if sig < 2:
                factor_multiple = 2.0
            elif sig < 5:
                factor_multiple = 2.0
            else:
                factor_multiple = 1.0
            
            
            factor = 10**(numpy.floor(numpy.log10(number*factor_multiple)))/factor_multiple
            rounded = numpy.ceil(number/factor)*factor
            print number, rounded
            return rounded
            
        self.xbound = 0
        self.bounds = {}
        for unit in self._get_units():
            self.bounds[unit]=[float('inf'), -float('inf')]
            
        for param in self.get_selected_parameters():
            unit = self.state.get_attribute_units(param)
            yv = numpy.asarray(self.state[param])/self.state.attributes[param]['scale']
            self.bounds[unit][0] = min(self.bounds[unit][0], numpy.nanmin(yv))
            self.bounds[unit][1] = max(self.bounds[unit][1], numpy.nanmax(yv))
            self.bounds[unit][0] = sig_round(self.bounds[unit][0])
            self.bounds[unit][1] = sig_round(self.bounds[unit][1])            
            if SIM_TYPE == SIM_DYNAMIC:
                self.xbound = max(self.xbound,len(self.state[param])-1)
        if SIM_TYPE == SIM_STATIC:
            if MG_TYPE == MG_QUOTA:
                self.xbound = numpy.nanmax(numpy.asarray(self.state['catch'])/self.state.attributes['catch']['scale'])
                
            else:
                self.xbound = numpy.nanmax(numpy.asarray(self.state['effort'])/self.state.attributes['effort']['scale'])
            self.xbound = sig_round(self.xbound)

       
    def get_selected_parameters(self):
        '''Return the parameters that have been selected for plotting'''
        out = []
        for param in self.state.attribute_order:
            if self.check_boxes[param].GetValue():
                out.append(param)
        return out
                
    def _get_units(self):
        '''
        Returns a list of units that will be plotted
        '''
        units = {}
        for param in self.get_selected_parameters():
            units[self.state.get_attribute_units(param)]=1
        
        return units.keys()

    def _setup_axes(self):
        '''
        Redraw the figure from scratch
        required if the number of axes etc. have changed
        '''
        
        #Clear the figure
        self.fig.clf()

        #Add the new axes
        self.axes = {}
        self.plot_data = {}
        self.axes_xscale = {}
        
        max_width = 0.87
        width_increment = 0.07
        bottom_space = .13
        pos=[.05, bottom_space, max_width-width_increment*(len(self._get_units())-1), 1-bottom_space-0.05]
        
        #Create the axes, one for each unit
        for unit in self._get_units():
            first_figure = len(self.axes)==0
            colour = self.unit_colour[unit]
            
            self.axes[unit] = self.fig.add_axes(pos,frameon=True,label=unit)
            self.axes[unit].yaxis.tick_right()
            self.axes[unit].yaxis.set_label_position('right')
            self.axes[unit].set_ylabel(unit)

            self.axes_xscale[unit] = pos[2]/(max_width-width_increment*(len(self._get_units())-1))
            if not first_figure:
                self.axes[unit].patch.set_alpha(0)
            else:
                self.firstaxes = self.axes[unit]
                self.axes[unit].set_xlabel('Years')
            self._modify_axes(self.axes[unit],colour,not first_figure)
            
            pos[2] += width_increment
            
        #Create the plot lines, one for each parameter
        for param in self.get_selected_parameters():
            unit = self.state.get_attribute_units(param)
            colour = self.unit_colour[unit]
            style = self.parameter_style[param]
            
            self.plot_data[param] = self.axes[unit].plot([0,0],[0,0],linewidth=2)[0]
            self.plot_data[param].set_color(colour)
            self.plot_data[param].set_dashes(style)
            
        #Text for npv
        self.npvtext = self.fig.text(.1,bottom_space,'NPV')
            
    def redraw(self,event=None,redraw=False):
        '''
        Update the plots using data in the current state
        '''
        if self.state == None:
            return  

        if not hasattr(self,'last_selected_parameters'):
            self.last_selected_parameters = {}
        
        #If the selected parameters have changed we need new axes
        if self.last_selected_parameters != self.get_selected_parameters() or redraw:
            self.last_selected_parameters = self.get_selected_parameters()
            self._colour_control()
            self._setup_axes()
              
        self._update_bounds()

        #Update axes bounds
        for unit in self._get_units():
            bounds = self.bounds[unit]
            self.axes[unit].set_ybound(lower = 0,upper = bounds[1])
            self.axes[unit].set_xbound(lower = 0,upper=self.xbound*self.axes_xscale[unit])

        #Update plot data
        for param in self.get_selected_parameters():
            data = self.state[param]
            if SIM_TYPE == SIM_DYNAMIC:
                self.plot_data[param].set_xdata(range(len(data)))
            else:
                if MG_TYPE == MG_QUOTA:
                    self.plot_data[param].set_xdata(numpy.asarray(self.state['catch'])/self.state.attributes['catch']['scale'])
                else:
                    self.plot_data[param].set_xdata(numpy.asarray(self.state['effort'])/self.state.attributes['effort']['scale'])
            self.plot_data[param].set_ydata(numpy.asarray(data)/self.state.attributes[param]['scale'])
        
        if SIM_TYPE == SIM_DYNAMIC:
            self.firstaxes.set_xlabel('Years')
        else:
            if MG_TYPE == MG_QUOTA:
                xunit = 'catch'
            else:
                xunit = 'effort'
            self.firstaxes.set_xlabel('Management Control: ' + self.state.attributes[xunit]['title'] + ' (' + self.state.attributes[xunit]['units'] + ')')   
            
        if SIM_TYPE == SIM_DYNAMIC and ~numpy.isnan(self.npv):
            self.npvtext.set_text('NPV: $' + str(int(round(self.npv/self.state.attributes['revenue']['scale']))) + ' million')
        else:
            self.npvtext.set_text('')
        self.canvas.draw()
        
    @staticmethod
    def _modify_axes(axes,color,remove = False):
        '''
        Set the colour of the y axis to color and optionally 
        remove the remaining borders of the graph   
        '''
        def modify_all(object,color=None,remove=False):
            for child in object.get_children():
                modify_all(child,color,remove)
            
            if remove and hasattr(object,'set_visible'):
                object.set_visible(not remove)
            
            if color != None and hasattr(object,'set_color'):
    
                object.set_color(color)
                        
        for child in axes.get_children():
            if isinstance(child, matplotlib.spines.Spine):
                if child.spine_type == 'right':
                    modify_all(child,color=color)
                elif remove == True:
                    modify_all(child,remove=True)
        
        modify_all(axes.yaxis,color=color)
        if remove:
            modify_all(axes.xaxis,remove=True)

class AboutBox(wx.Dialog):
    '''An about dialog box, which displays a html file'''
    replacements = {'_VERSION_': VERSIONSTRING}
    def __init__(self,parent,title,filename):
        '''
        parent: parent window
        title: dialog box title
        filename: the html file to show
        '''
        wx.Dialog.__init__(self,parent,-1,title,size=(500,550))
        
        #Read the html source file
        fid = open(filename,'r')
        self.abouthtml = fid.read()
        fid.close()
        
        #Replace tokens
        for key in self.replacements.keys():
            self.abouthtml = self.abouthtml.replace(key,self.replacements[key])
        
        
        self.html = wx.html.HtmlWindow(self)
        self.html.SetPage(self.abouthtml)
        
        self.ok_button = wx.Button(self,wx.ID_OK,"Ok")
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.html,1,wx.EXPAND|wx.ALL,5)
        self.sizer.Add(self.ok_button,0,wx.ALIGN_CENTER|wx.ALL,5)
        self.SetSizer(self.sizer)
        self.Layout()

x=1366
y=768
class App(wx.App):
    def OnInit(self):
        self.frame = Frame(x,y)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        self.frame.Layout()
        
        
        return True
    
if __name__ == '__main__':
    app = App(redirect=False)
#    app = App(redirect=False)
	
    app.MainLoop()    


