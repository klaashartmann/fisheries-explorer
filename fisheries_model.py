#!/usr/bin/env python

'''
Fisheries Economics Masterclass model
Copyright 2010,2016 University of Tasmania, Australian Seafood CRC
This program is released under the Open Software License ("OSL") v. 3.0. See OSL3.0.htm for details.
'''

import threading
import wx
from pylab import *
import copy

class Parameter(dict):
    """
    Model parameter class
    A simple dict with some default values
    """
    
    def __init__(self,value=0,min=0,max=1,units='',title='',description='',type='Miscellaneous',scale=1,scale_text=''):
        """Initialise the parameter"""
        self['value'] = value
        self['min'] = min
        self['max'] = max
        self['units'] = units
        self['title'] = title
        self['description'] = description
        self['type'] = type
        self['scale'] = scale
        self['scale_text']=scale_text

class Component:
    """
    Model component class
    All model classes should inherit this
    """ 
    
    def get_parameters(self):
      """
      Returns the parameters required by this component
      The format is a dictionary, keys are parameter name, value is a list of
      minimum value, maximum value, default value,
      """ 
      return {}
  
  
    def execute(self,state,parameters):
      """Executes this component and returns the modified state"""
      return state

class PDLogistic(Component):
    """Population Dynamics Logistic growth component"""
  
    def __init__(self):
        self.r = Parameter(title='Population growth rate',
                           description='The maximum growth rate of the population',
                           type='Population dynamics')
        self.K = Parameter(title='Maximum population size',
                           description='The size of a unfished (virgin) population',
                           type='Population dynamics')
  
    def get_parameters(self):
        return {'r': self.r,'K': self.K}
    
  
    #Execute a logistic step
    def execute(self,state,parameters,equilibrium=False):
        if equilibrium:
            r = parameters['r']
            K = parameters['K']
            if parameters.has_key('catch'):
                C = parameters['catch']
                # [r-1 + (1-2r+r2+4Cr/K)^.5]/(2r/K)
                term = (r)**2-4*C*r/K
                #term = (1-4*parameters['catch']/parameters['r']/parameters['K'])
                if term < 0:
                    state['biomass'][-1] = 0
                else:
                    #state['biomass'][-1] = parameters['K']/2*(1+term**0.5)#+parameters['catch'] #Catch is added back on as the catch step removes it
                    state['biomass'][-1] = (r+term**.5)/(2*r/K)
                    state['biomass'][-1] += parameters['catch'] #Catch is added back on as the catch step removes it
            else:
                catch = state['biomass'][-1]* parameters['catch_rate']*parameters['effort']/parameters['K']
                state['biomass'][-1] = parameters['K']-parameters['catch_rate']*parameters['effort']/parameters['r']
                state['biomass'][-1] += catch 
                #state['biomass'][-1] = K*(1-r)
        else:
            b = state['biomass'][-1]
            state['biomass'][-1] = b+b*parameters['r']*(1-b/parameters['K'])
        return state

#Catch component removes catch determines CPUE
class CatchFixed(Component):
    """Fixed catch component with simplistic CPUE/effort calculation"""
    
    catch_rate = Parameter(title='Max catch rate',
                           description='The biomass caught per unit of effort',
                           type='Fleet dynamics')
    catch = Parameter(title='TAC',
                      description='Total allowable catch',
                      type='Management Controls'
                      )        
    
    def get_parameters(self):
        return {'catch_rate': self.catch_rate, 'catch': self.catch}
  
    def execute(self,state,parameters,equilibrium=False):
        preCatchBiomass = state.get('biomass')
        previousBiomass = state['biomass'][-2]
    
        state.set(cpue=previousBiomass/parameters['K']*parameters['catch_rate'])
        state.set(biomass=preCatchBiomass-parameters['catch'])
        state.set(catch=parameters['catch'])
        if state.get('biomass') < 0:
            state.set(biomass=0,catch= preCatchBiomass)
        
        if state.get('cpue') <= 0:
            state.set(effort=0)
        else:
            state.set(effort=state.get('catch')/state.get('cpue'))

        return state
    

#Constant effort
class EffortFixed(Component):
    """Fixed catch component with simplistic CPUE/effort calculation"""
    
    catch_rate = Parameter(title='Max catch rate',
                           description='The biomass caught per unit of effort',
                           type='Fleet dynamics')
    effort = Parameter( title='Effort',
                        description='Fishing effort',
                        type='Management Controls'
                        )
    
    def get_parameters(self):
        return {'catch_rate': self.catch_rate, 'effort': self.effort}
  
    def execute(self,state,parameters,equilibrium=False):
        previousBiomass = state['biomass'][-2]
        preCatchBiomass = state['biomass'][-1]

        state.set(cpue=previousBiomass/parameters['K']*parameters['catch_rate'])
        state.set(catch=parameters['effort']*state.get('cpue'))
        state.set(biomass=preCatchBiomass-state.get('catch'))
        if state.get('biomass') < 0:
            state.set(biomass=0,catch= preCatchBiomass)
        state.set(effort=parameters['effort'])
        
        return state

      
class Economics(Component):
  
    fixed_cost   = Parameter(     title='Operator fixed cost',
                                  description='An individual operator\s fixed annual cost',
                                  type='Economics')
    marginal_cost= Parameter(     title='Operator marginal cost',
                                  description='An individual operator\s marginal cost per unit effort',
                                  type='Economics')
    movement_rate= Parameter(     title='Fleet resize rate',
                                  description='The maximum rate at which vessels can enter or exit the fishery',
                                  type='Fleet dynamics')
    beach_price  = Parameter(     title='Beach price',
                                  description='The price per kg of landed fish',
                                  type='Economics')
    discount_rate = Parameter(    title='Discount Rate',
                                  description='The discount rate',
                                  type='Economics')
    
    def get_parameters(self):
        return {'fixed_cost': self.fixed_cost,
                'marginal_cost': self.marginal_cost,
                'movement_rate': self.movement_rate,
                'beach_price': self.beach_price,
                'discount_rate': self.discount_rate}
    
    @staticmethod
    def _calculate_revenue(state,parameters):
        return state.get('catch')*parameters['beach_price']   
    
    @staticmethod
    def _calculate_cost(state,parameters):
        return (state.get('fleet_size')*parameters['fixed_cost']+\
               state.get('effort')*parameters['marginal_cost'])
    
    @staticmethod
    def _calculate_profit(state,parameters):
        return Economics._calculate_revenue(state,parameters)-Economics._calculate_cost(state,parameters)
    
    def execute(self,state,parameters,equilibrium=False):

        #Adjust the fleet size
        original_fleet_size = state.get('fleet_size')
        while abs(self._calculate_profit(state,parameters))>parameters['fixed_cost'] and \
              ((equilibrium and parameters['movement_rate'] > 0) or 
               abs(original_fleet_size - state.get('fleet_size')) < parameters['movement_rate']):
            if self._calculate_profit(state,parameters) > 0:
                state.set(fleet_size = state.get('fleet_size')+1)
            else:
                state.set(fleet_size = state.get('fleet_size')-1)  
        
        #Set the cost, revenue and profit        
        state.set(cost = self._calculate_cost(state, parameters))
        state.set(revenue = self._calculate_revenue(state,parameters))
        profit = state.get('revenue')-state.get('cost')
        if abs(profit)<1000000:
            profit = 0
        state.set(profit = profit)
        
        state.set(discounted_profit = profit*(1-parameters['discount_rate'])**(len(state['cost'])-2))
        
        return state
            
            
            
                                
             

class State(dict):
    """Model state
    A dictionary where each key corresponds to an attribute of a fishery state (eg. biomass)
    all keys are the same length and can be extended trivially
    """
       
    def __init__(self, attributes):
        """
        Constructor
        
        attribute_list is a dictionary for the attributes of the fishery
        see example fishery models for details
        """
        for key in attributes:
            self[key] = [nan]
        
        self.attributes = attributes
        self.attribute_order = self.attributes.keys()
        #The attributes to plot first up by default
        self.default_plot = self.attributes.keys()
        
        self.unit_order = []
        units = {}
        
        for att in self.attributes:
            unit = self.attributes[att]['units']
            if not units.has_key(unit):
                units[unit]=1
                self.unit_order.append(unit) 
    
    def extend(self):
        """Extend all the lists by one, using the previous value for the new value"""
        for att in self:
            self[att].append(self[att][-1])
        return
    
    def set(self,**kwargs):
        """Set the current (last item) of one or more of the lists"""
        for key in kwargs:
            self[key][-1]=kwargs[key]
            
    def get(self,item):
        """Get the current (last item) of one of the lists"""
        return self[item][-1]
    
    def get_attribute_title(self,attribute):
        return self.attributes[attribute]['title']

    def get_attribute_units(self,attribute):
        return self.attributes[attribute]['units']
    

    
    def reset(self):
        """
        Resets the state to the initial timestep
        """
        for att in self:
            self[att]=self[att][0:1]
        return
    
class Model():
    """Model Definition
    By combining a set of model functions this class creates a complete
    model definition"""
    
    def __init__(self,functions=[],parameters={},initial_state = None,convergence_time=3):
        """
        functions: a list of functions in the order that they are to be run
        parameters: a dict of parameters as required by the functions (can be set later)
        initial_state: initial state of the fishery
        convergence_time: number of steps required to convergence of static version
        """
        if initial_state == None:
            self.state = State()
        else:
            self.state = initial_state
            
        self.functions = functions
        self.parameters = parameters
        self.convergence_time = convergence_time
    
    def get_parameters(self):
        """
        returns a list of parameters as required by the model functions
        """ 
        #Get all parameters
        pOut = {}
        for function in self.functions:
            pOut.update(function.get_parameters())
            
        #Replace values with current if applicable
        for param in pOut:
            if self.parameters.has_key(param):
                pOut[param].value = self.parameters[param]
        
        return pOut
    
    def set_parameters(self,parameters):
        """
        set the parameters to a given value for this and subsequent time steps
        """
        self.parameters = parameters
        
    def get_parameter_types(self):
        """
        return a list of parameter types
        """
        types = {}
        p = self.get_parameters()
        for par in p:

            types[p[par]['type']] = 1
        
        return types.keys()
    
        
        
    def set_state(self,state):
        """
        set the state of the model
        """
        self.state = state
        
    def reset(self):
        """
        Resets the model state to the initial timestep
        """
        self.state.reset()
        
    
    def run(self,steps = 1,constant_variable=None):
        """
        run the model for one time step
        """
        for step in range(0,steps):
            self.state.extend()
            for function in self.functions:
                self.state=function.execute(self.state,self.parameters,equilibrium=constant_variable!=None)

class MultiThreadModelRun:
    class MyThread(threading.Thread):

        def __init__(self,function):
            '''Initialise the thread:
            function: a function to be called after run completion
            '''
            threading.Thread.__init__(self)
            self.function = function        
            self.update = False
            self.cancel_run = False

        def update_run(self,model,steps,options):
            '''Start a new run
            model: the model to use
            options: the run options
            '''
            self.newmodel = copy.deepcopy(model)
            self.newsteps = steps
            self.newoptions = options
            self.update = True
        
        def run(self):
            '''The thread's run function'''
            import time
            while True:
                #Cancelling the thread's run for now
                if self.cancel_run:
                    self.cancel_run = False
                    self.update = False
                #Creating a new run 
                if self.update:
                    self.model = self.newmodel
                    self.options = self.newoptions
                    self.steps = self.newsteps
                    self.update = False
                    
                    for step in range(0,self.steps):
                        if self.update:
                            break
                        self.single_iteration(step)
                        
                    if not self.update:
                        if not self.function==None:
                            wx.CallAfter(self.function,self.output())
                else:
                    time.sleep(0.01)
                    pass

        def cancel(self):
            '''Cancel this run'''
            self.update = True
            self.cancel_run = True

        def single_iteration(self,step):
            '''Perform a single iteration (to be implemented by inheriting class)'''
            pass

        def output(self):
            '''Return the model output (to be implemented by inheriting class)'''
            pass

    class DynamicThread(MyThread):
        '''Thread for dynamic model runs'''

        def single_iteration(self,step):
            '''Run a single time step'''
            self.model.run(1)

        def output(self):
            '''Return the model state'''
            return self.model.state

    class StaticThread(MyThread):
        '''Thread for static model runs'''
        def update_run(self,model,steps,options):
            '''Update the run, copying a new output state as well'''
            #MultiThreadModelRun.MyThread.update_run(self,model,steps,options)
            self.newmodel = copy.deepcopy(model)
            self.newsteps = steps
            self.newoptions = options
            self.update = True
            self.output_state = copy.deepcopy(self.newmodel.state)
            self.output_state.reset()

        def single_iteration(self,step):
            '''Find an equilibrium state for a single independent parameter value'''
            #Reset the model 
            self.model.reset()
            #Set the independent value to the appropriate value
            self.model.state[self.options['independent_variable']] = [self.options['independent_values'][step]]
            self.model.parameters[self.options['independent_variable']] = self.options['independent_values'][step]
            self.model.run(self.options['convergence_time'],constant_variable = self.options['independent_variable'])
            if True: #self.model.state[self.options['independent_variable']][-1] == self.options['independent_values'][step]:
                for param in self.model.state.keys():
                    self.output_state[param].append(self.model.state[param][-1])
            if self.model.state[self.options['independent_variable']][-1] < self.options['independent_values'][step]:
                self.output_state[self.options['independent_variable']][-1] = self.options['independent_values'][step-1]+1e-6
#            self.output_state[self.options['independent_variable']][-1] = self.options['independent_values'][step]

        def output(self):
            '''Return the output state'''
            return self.output_state
            

    def __init__(self,function=None):
        self.static_thread = self.StaticThread(function)  
        self.static_thread.start()
        self.dynamic_thread = self.DynamicThread(function)  
        self.dynamic_thread.start()
        
    def run(self,model,steps,dynamic=True,independent_variable='effort',independent_minimum = 0,independent_maximum = None,convergence_time=4):

        if dynamic:
            self.static_thread.cancel()
            self.dynamic_thread.update_run(model,steps,{})
        else:
            self.dynamic_thread.cancel()
            self.static_thread.update_run(model,steps,
                {   'independent_variable': independent_variable,
                    'independent_values': linspace(independent_minimum,independent_maximum,steps),
                    'convergence_time':convergence_time})
    
def lobsterModel(control_type = 'catch'):
    
    '''A lobster model, loosely based on the Tasmanian Rock Lobster Fishery'''
    
    #------------------------------------------
    #Parameter values customised for this model
    #------------------------------------------
    
    r =         {'value':1,'min':0,'max':2}
    K =         {'value':7000000,'min':0,'max':10000000,'scale':1000,'units':'t'}
    catch_rate ={'value':1,'min':0.001,'max':5,'units':'kg/potlift'}
    catch =     {'value':1500000,'min':0,'max':6000000,'scale':1000,'units':'t'}
    effort =    {'value':1500000,'min':0,'max':5000000,'description':'Number of potlifts','scale':1e6,'scale_text':'millions'}
    fixed_cost ={'value':100000,'min':50000,'max':200000,'units':'$/year','scale':1000,'scale_text':'thousands'}
    marginal_cost= {'value':30,'min':5,'max':50,'units':'$/potlift'}
    movement_rate={'value':0,'min':0,'max':20,'units':'vessels/year'}
    beach_price  = {'value':60,'min':0,'max':100,'units':'$/kg'}
    discount_rate = {'value':0.07,'min':0,'max':1,'units':''}

    #-----------------------------------------
    #Functions that control the model dynamics
    #-----------------------------------------

    #Discrete logistic growth
    growthClass = PDLogistic()
    growthClass.r.update(r)
    growthClass.K.update(K)

    #Catch component
    if control_type == 'catch':
        catchClass = CatchFixed()
        catchClass.catch.update(catch)
    elif control_type == 'effort':
        catchClass = EffortFixed()
        catchClass.effort.update(effort)
    catchClass.catch_rate.update(catch_rate)
    
    #Economics and fleet dynamics
    economicsClass = Economics()
    economicsClass.fixed_cost.update(fixed_cost)
    economicsClass.marginal_cost.update(marginal_cost)
    economicsClass.movement_rate.update(movement_rate)
    economicsClass.beach_price.update(beach_price)
    economicsClass.discount_rate.update(discount_rate)

    #-----------------------------------------
    #Set the state of the fishery
    #The attributes here must match what is 
    #required by the functions PDLogistic,
    #CatchFixed/EffortFixed and Economics
    #-----------------------------------------
    initial_state = State(
            attributes = {'biomass': {'title': 'Biomass', 'units': 'tonnes','scale':1000},
                          'catch': {'title': 'Catch', 'units': 'tonnes','scale':1000},
                          'cpue': {'title': 'CPUE', 'units': 'kg/potlift','scale':1},
                          'effort': {'title': 'Effort', 'units': 'millions of potlifts','scale':1e6},
                          'fleet_size': {'title': 'Fleet Size','units': '# vessels','scale':1},
                          'revenue': {'title': 'Revenue','units': '$ (millions)','scale':1e6},
                          'cost': {'title': 'Cost','units': '$ (millions)','scale':1e6},
                          'profit': {'title': 'Profit','units': '$ (millions)','scale':1e6},
                          'discounted_profit': {'title': 'Discounted profit','units': '$ (millions)','scale':1e6},
                          })
    initial_state.default_plot = ['biomass','catch']
#    initial_state.default_plot = ['catch','revenue','cost','profit']
    initial_state.attribute_order = ['biomass','catch','profit','revenue','cost','discounted_profit','cpue','effort','fleet_size']
    #Set the initial fishery parameters
    initial_state.set(biomass=5000000,fleet_size=120)

    #-----------------------------------------
    #Create the fishery model
    #-----------------------------------------
    model = Model(functions = [growthClass,catchClass,economicsClass],initial_state = initial_state)

    return model

    
def fishModel(control_type = 'catch'):
    
    '''A generic fish/net model'''
    
    #As compared to RL:
    #catch rate * 100
    #K / 10
    #catch / 10
    #Effort / 100
    #Marginal cost * 100
    #Fixed Cost / 10
    
    #------------------------------------------
    #Parameter values customised for this model
    #------------------------------------------
    
    r =         {'value':1,'min':0,'max':2}
    K =         {'value':700000,'min':0,'max':1000000,'scale':1000,'units':'t'}
    catch_rate ={'value':100,'min':1,'max':500,'units':'kg/day'}
    catch =     {'value':150000,'min':0,'max':600000,'scale':1000,'units':'t'}
    effort =    {'value':1500,'min':0,'max':5000,'description':'Days fished'}
    fixed_cost ={'value':10000,'min':5000,'max':20000,'units':'$/year','scale':1000,'scale_text':'thousands'}
    marginal_cost= {'value':1000,'min':500,'max':5000,'units':'$/day'}
    movement_rate={'value':0,'min':0,'max':20,'units':'vessels/year'}
    beach_price  = {'value':30,'min':0,'max':60,'units':'$/kg'}
    discount_rate = {'value':0.07,'min':0,'max':1,'units':''}

    #-----------------------------------------
    #Functions that control the model dynamics
    #-----------------------------------------

    #Discrete logistic growth
    growthClass = PDLogistic()
    growthClass.r.update(r)
    growthClass.K.update(K)

    #Catch component
    if control_type == 'catch':
        catchClass = CatchFixed()
        catchClass.catch.update(catch)
    elif control_type == 'effort':
        catchClass = EffortFixed()
        catchClass.effort.update(effort)
    catchClass.catch_rate.update(catch_rate)
    
    #Economics and fleet dynamics
    economicsClass = Economics()
    economicsClass.fixed_cost.update(fixed_cost)
    economicsClass.marginal_cost.update(marginal_cost)
    economicsClass.movement_rate.update(movement_rate)
    economicsClass.beach_price.update(beach_price)
    economicsClass.discount_rate.update(discount_rate)

    #-----------------------------------------
    #Set the state of the fishery
    #The attributes here must match what is 
    #required by the functions PDLogistic,
    #CatchFixed/EffortFixed and Economics
    #-----------------------------------------
    initial_state = State(
            attributes = {'biomass': {'title': 'Biomass', 'units': 'tonnes','scale':1000},
                          'catch': {'title': 'Catch', 'units': 'tonnes','scale':1000},
                          'cpue': {'title': 'CPUE', 'units': 'kg/day','scale':1},
                          'effort': {'title': 'Effort', 'units': 'Days fished','scale':1000},
                          'fleet_size': {'title': 'Fleet Size','units': '# vessels','scale':1},
                          'revenue': {'title': 'Revenue','units': '$ (millions)','scale':1e6},
                          'cost': {'title': 'Cost','units': '$ (millions)','scale':1e6},
                          'profit': {'title': 'Profit','units': '$ (millions)','scale':1e6},
                          'discounted_profit': {'title': 'Discounted profit','units': '$ (millions)','scale':1e6},
                          })
    initial_state.default_plot = ['biomass','catch']
#    initial_state.default_plot = ['catch','revenue','cost','profit']
    initial_state.attribute_order = ['biomass','catch','profit','revenue','cost','discounted_profit','cpue','effort','fleet_size']
    #Set the initial fishery parameters
    initial_state.set(biomass=500000,fleet_size=20)

    #-----------------------------------------
    #Create the fishery model
    #-----------------------------------------
    model = Model(functions = [growthClass,catchClass,economicsClass],initial_state = initial_state)

    return model



