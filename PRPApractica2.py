#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRÁCTICA 2: puente de Ambite

Apellidos: BALLESTEROS GÓMEZ 
Nombre:    GABRIELA 
"""

import time
import random
from multiprocessing import Lock, Condition, Process
from multiprocessing import Value


NORTH = 0
SOUTH = 1
PED=2 
VACÍO= 100

NCARS = 100
NPED = 10
TIME_CARS_NORTH = 0.5  # a new car enters each 0.5s
TIME_CARS_SOUTH = 0.5  # a new car enters each 0.5s
TIME_PED = 5 # a new pedestrian enters each 5s
TIME_IN_BRIDGE_CARS = (1, 0.5) # normal 1s, 0.5s
TIME_IN_BRIDGE_PEDESTRIAN = (30, 10) # normal 1s, 0.5s

class Monitor():
    def __init__(self):
        self.mutex = Lock()
        self.patata = Value('i', 0)
        
        self.car_bridge=[Value('i',0),Value('i',0)]#lista con variable compartida de dos posiciones, [0] north y [1] sur??
        self.car_queue=[Value('i',0),Value('i',0)] #lista de coches esperando a entrar de cada lado 
        
        self.peaton_bridge=Value('i',0) #como los peatones entran al mismo tiempo de ambos lados no distingo 
        self.peaton_queue=Value('i',0)
        
        self.southway=Condition(self.mutex)
        self.northway=Condition(self.mutex)
        self.peatonway=Condition(self.mutex)
        
        self.sentido=Value('i',100) 
        
    
    def goingSouth(self): #para ver si pueden pasar del norte 
        return ((self.peaton_bridge.value==0 and self.car_bridge[1].value==0) and (self.sentido.value==NORTH or self.sentido.value==100))
    
    def goingNorth(self): #para ver si pueden pasar del sur 
        return ((self.peaton_bridge.value==0 and self.car_bridge[0].value==0) and (self.sentido.value==SOUTH or self.sentido.value==100))
    
    def goingPeaton(self):#para ver si pueden pasar peatones 
        return ((self.car_bridge[0].value==0 and self.car_bridge[1].value==0) and (self.sentido.value==PED or self.sentido.value==100))
    
    
    def wants_enter_car(self, direction: int) -> None:
        self.mutex.acquire()
        self.patata.value += 1
            
        self.car_queue[direction].value+=1 #le meto a la cola de los que quieren entrar
        if direction==NORTH:
            self.northway.wait_for(self.goingSouth) #espero a poder pasar 
            self.sentido.value=0
            
        elif direction==SOUTH:
            self.southway.wait_for(self.goingNorth) #espero a poder pasar 
            self.sentido.value=1 #me aseguro de activar su dirección (sobre todo para el caso en el cual sentido=100 )

        self.car_queue[direction].value-=1#ya ha entrado así que no está esperando    
        self.car_bridge[direction].value+=1 #indico que está en el puente 
        
        
        self.mutex.release()

    def leaves_car(self, direction: int) -> None:
        self.mutex.acquire() 
        self.patata.value += 1
        self.car_bridge[direction].value-=1 #termina de cruzar el puente
            
        if direction==NORTH:
            if self.car_queue[1].value>self.peaton_queue.value and self.car_queue[1]!=0:
                self.sentido.value=1 #si hay más coches del sur en espera que peatones, pasan los coches 
                
            elif self.car_queue[1].value<=self.peaton_queue.value and self.peaton_queue.value!=0:
                self.sentido.value=2 #viceversa 
             
            else:
                self.sentido.value=100 #si no hay ni coches ni peatones en espera, ponemos sentido neutro
                

            if self.car_bridge[0].value==0:#notificamos cuando han terminado de pasar los coches que estaban aún en el puente 
                self.peatonway.notify_all()
                self.southway.notify_all()
             
        else:#direction==SOUTH
            if self.car_queue[0].value>self.peaton_queue.value and self.car_queue[0]!=0:
                self.sentido.value=0 #si hay más coches en el norte que peatones
                
            elif self.car_queue[0].value<=self.peaton_queue.value and self.peaton_queue.value!=0:
                self.sentido.value=2 #viceversa
            
            else:
                self.sentido.value=100 #si no hay coches ni peatones en espera, ponemos sentido neutro 
    

            if self.car_bridge[1].value==0:#notificamos cuanod terminan de pasar los coches que estabn en el puente 
                self.peatonway.notify_all()
                self.northway.notify_all()
            
        self.mutex.release()

        
    def wants_enter_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        
        self.peaton_queue.value+=1 #meto al peatón en espera 
        self.peatonway.wait_for(self.goingPeaton) #espero a poder pasar 
        self.sentido.value=2 #verifico que el sentido en uso sea el mío 
        
        self.peaton_bridge.value+=1 #entro al puente
        self.peaton_queue.value-=1 #ya no estoy esperando 
        
        self.mutex.release()


    def leaves_pedestrian(self) -> None:
        self.mutex.acquire()
        self.patata.value += 1
        
        self.peaton_bridge.value-=1
        
        if self.car_queue[0].value>self.car_queue[1].value and self.car_queue[0].value!=0:
            self.sentido.value=0#si hay más coches en espera en el norte que en el sur, pasa el norte
            
        elif self.car_queue[0].value<=self.car_queue[1].value and self.car_queue[1].value!=0:
            self.sentido.value=1#si hay más coches en espera en el sur que en el norte, pasa el sur 
        
        else: 
            self.sentido.value=100 #si no hay nadie esperando pongo sentido neutro 
        
        if self.peaton_bridge.value==0:#notifico a todos cuando han terminado de pasar los peatones que estaban en el puente aún 
            self.southway.notify_all()
            self.northway.notify_all()
            

        self.mutex.release()
        

    def __repr__(self) -> str:
        #a=f'Monitor: {self.patata.value}, sentido: {self.sentido.value} '
        #b=f'coches puente norte: {self.car_bridge[0].value}, coches puente sur: {self.car_bridge[1].value}, peatones puente: {self.peaton_bridge.value}'
        #c=f'waitingNorte: {self.car_queue[0].value}, waitingSur:{self.car_queue[1].value}, peatones: {self.peaton_queue.value}'
        #return a+'\n'+b+'\n'#+c
        return f'Monitor: {self.patata.value}'
    
def delay_car_north(factor=3) -> None:
    time.sleep(random.random())

def delay_car_south(factor=3) -> None:
    time.sleep(random.random())

def delay_pedestrian(factor=3) -> None:
    time.sleep(random.random())
    

    

def car(cid: int, direction: int, monitor: Monitor)  -> None:
    print(f"->car {cid} heading {direction} wants to enter. {monitor}")
    monitor.wants_enter_car(direction)
    print(f"->car {cid} heading {direction} enters the bridge. {monitor}")
    if direction==NORTH :
        delay_car_north()
    else:
        delay_car_south()
    print(f"->car {cid} heading {direction} leaving the bridge. {monitor}")
    monitor.leaves_car(direction)
    print(f"->car {cid} heading {direction} out of the bridge. {monitor}")

def pedestrian(pid: int, monitor: Monitor) -> None:
    print(f"->pedestrian {pid} wants to enter. {monitor}")
    monitor.wants_enter_pedestrian()
    print(f"->pedestrian {pid} enters the bridge. {monitor}")
    delay_pedestrian()
    print(f"->pedestrian {pid} leaving the bridge. {monitor}")
    monitor.leaves_pedestrian()
    print(f"->pedestrian {pid} out of the bridge. {monitor}")



def gen_pedestrian(monitor: Monitor) -> None:
    pid = 0
    plst = []
    for _ in range(NPED):
        pid += 1
        p = Process(target=pedestrian, args=(pid, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/TIME_PED))

    for p in plst:
        p.join()

def gen_cars(direction: int, time_cars, monitor: Monitor) -> None:
    cid = 0
    plst = []
    for _ in range(NCARS):
        cid += 1
        p = Process(target=car, args=(cid, direction, monitor))
        p.start()
        plst.append(p)
        time.sleep(random.expovariate(1/time_cars))

    for p in plst:
        p.join()

def main():
    monitor = Monitor()
    gcars_north = Process(target=gen_cars, args=(NORTH, TIME_CARS_NORTH, monitor))  
    gcars_south = Process(target=gen_cars, args=(SOUTH, TIME_CARS_SOUTH, monitor))
    gped = Process(target=gen_pedestrian, args=(monitor,))
    gcars_north.start()
    gcars_south.start()
    gped.start()
    gcars_north.join()
    gcars_south.join()
    gped.join()


if __name__ == '__main__':
    main()
