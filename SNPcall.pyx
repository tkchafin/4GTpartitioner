#!/usr/bin/python

import random
import pyximport; pyximport.install()

class SNPcall():
	def __init__(self, pos, samps):
		self.position = int(pos)
		self.POS=self.position
		self.calls = list(samps)
	
	def __lt__(self, other):
		return(self.position < other.position)


##############################################################################

	#TODO:try to speed this up. 32% of runtime currently
	def FGT(self, other, rule):
		#print("Four gamete test for",self.position,"and",other.position)
		gametes = [0,0,0,0] #00, 01, 10, 11
		hets = list()
		
		#TODO: This line takes a long time. 21% of total runtime 
		valid =set([0, 1, 2])
		genotypes = [[gt, other.calls[i]] for i, gt in enumerate(self.calls) if gt and other.calls[i] in valid]

		for geno in genotypes:
			gamete = self.hapCheck(geno)
			if gamete:
				gametes[gamete] = 1
			else:
				if 1 in geno:
					if rule == 1:
						if geno[0] == 1:
							geno[0] = random.choice([0,2])
						if geno[1] == 1:
							geno[1] = random.choice([0,2])
						#print(geno)
						gametes[self.hapCheck(geno)] = 1
					elif rule == 2:
						possible1 = list()
						possible2 = list()
						if geno[0] == 1:
							possible1 = [0,2]
						else:
							possible1 = [geno[0]]
						if geno[1] == 1:
							possible2 = [0,2]
						else:
							possible2 = [geno[1]]
						for i in possible1:
							for j in possible2:
								gametes[self.hapCheck([i,j])] = 1
					elif rule == 3:
						hets.append(geno)
		if sum(gametes) == 4:
			return(False) #return False if not compatible
		elif hets:
			if not self.optimisticFGT(gametes, hets):
				return(False) #return false if not compatible 
			else:
				return(True)
		else:
			return(True)
############################################################################
	
	@staticmethod
	#TODO: Optimize; currently 11% of runtime after 2X speedup
	def hapCheck(geno):
		if geno[0] == 0:
			if geno[1] == 0:
				return(0)
			elif geno[1] ==2:
				return(1)
			else:
				return(None)
		elif geno[0] == 2:
			if geno[1] == 0:
				return(2)
			elif geno[1] ==2:
				return(3)
			else:
				return(None)
		else:
			return(None)
	
	def optimisticFGT(self, seen, hets):
		possibilities = list()
		for het in hets:
			locals = list()
			possible1 = list()
			possible2 = list()
			if het[0] == 1:
				possible1 = [0,2]
			else:
				possible1 = [het[0]]
			if het[1] == 1:
				possible2 = [2,0]
			else:
				possible2 = [het[1]]
			for i in possible1:
				for j in possible2:
					copy = seen[:] #deep copy
					copy[self.hapCheck([i,j])] = 1
					locals.append(copy)
			possibilities = locals[:]
		#print(possibilities)
		for opt in possibilities:
			#print(opt)
			if sum(opt) != 4: #if ANY possibilities 
				return True #return False if not compatible
		return(False)