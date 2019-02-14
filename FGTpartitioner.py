#!/usr/bin/python

import re
import sys
import os
import getopt
import vcf
import pysam
import random
import collections
import operator
import intervaltree
from intervaltree import Interval, IntervalTree
from collections import OrderedDict 

def main():
	params = parseArgs()

	print("Opening VCF file:",params.vcf)
	vfh = vcf.Reader(filename=params.vcf)

	#grab contig sizes
	contigs = dict()
	if params.chrom:
		print("Only reading chromosome:",params.chrom)
	else:
		print("Reading all chromosomes from VCF...")
	
	for c,s in vfh.contigs.items():
		if params.chrom and s.id != params.chrom:
			continue
		contigs[s.id] = s.length

	if len(contigs) < 1:
		print("No chromosomes found. Please check your input or verify that options provided with -c are correct")
		sys.exit(1)
		
	'''
	1. for each chromosome (or 1 if region is set)
	2. build list where value=SeqRecord
	3. next, loop through ordered dict to build IntervalTree
		Interval = start, end, index
		k_lookup[index] = k (order, or number of nodes encompassed)
	4. after examining last node, resolve tree
		from smallest k to largest k. Maybe sort k_lookup by value
	
	tree resolution: 
	For each layer from k=1 to kmax:
		for each interval in layer k
			query center point of interval to get interval depth
			if overlaps exist:
				query each SNP-node centerpoint between interval start and end
				place break at centerpoint which maximizes depth, or center of maximum depth region
				delete all intervals intersecting with breakpoint
	'''
	

	miss_skips=0
	allel_skips=0
	count=0
	
	print("Diploid resolution strategy: ", end="")
	if params.rule==1:
		print("Random", end="")
	elif params.rule==2:
		print("Pessimistic", end="")
	elif params.rule==3:
		print("Optimistic",end="")
	else:
		print("Invalid!",end="")
		sys.exit(1)
	print(" (change with -r)")
	
	#for each chromosome
	for this_chrom in contigs: 
		print("Checking", this_chrom)
		#initialize data structures
		tree = IntervalTree()
		k_lookup = dict()
		nodes = list()
		start = 0
		stop =1
		index=1 #keys for intervals
		
		#Gather relevant SNP calls from the VCF 
		records = vfh.fetch(this_chrom)
		if not records:
			print("Not enough records found for chromosome:",this_chrom)
		for rec in records:
			if rec.CHROM != this_chrom:
				continue
			else:
				#if this SNP
				if rec.is_snp and not rec.is_monomorphic and not rec.is_indel:
					if rec.num_called < 4:
						miss_skips +=1
					elif len(rec.alleles) > 2:
						allel_skips +=1
					else:
						#print(rec.samples)
						samps = [s.gt_type for s in rec.samples]
						nodes.append(SNPcall(rec.POS, samps))
						count+=1
						
						'''
	*********************** Remove after testing ********************
						'''
						if count >= 1000:
							break

						'''
	******************************************************************
						'''
		
		#Traverse node list to find FGT conflicts
		if len(nodes) > 2:
			start = 0
			end = 1
			while start <= len(nodes):
				#print("Start=",start)
				#print("End=",end)
				if end >= len(nodes):
					start = start + 1
					end= start + 1
					continue
				#Check if start and end are compatible
				compat = nodes[start].FGT(nodes[end], params.rule)
				if compat == True: #if compatible, increment end and continue 
					#print("Compatible! Checking next SNP")
					end+=1
					continue
				else: #if FGT fails, submit interval to IntervalTree, and increment start
					#print("Not compatible!")
					interval = Interval(nodes[start].position, nodes[end].position, end-start)
					k_lookup[count] = interval #k-layer for this interval
					tree.add(interval) #add interval from start.position to end.position
					count +=1 #increment key, so all will be unique
					start = start+1 #move start to next SNP 
					end = start+1 #reset end to neighbor of new start

			print("Found ",len(tree),"intervals.")
			#print(tree)
			
			#order k_lookup by k
			#NOTE: Over-rode the __lt__ function for Intervals: see __main__ below
			#otherwise this would sort on start position!
			sorted_k = sorted(k_lookup.items(), key=operator.itemgetter(1)) #gets ordered tuples
			#print(sorted_k)
			
			#start resolving from lowest k
			
			
			#remove resolved from tree 
			#pop off dictionionary 
			#for each interval: ask if still in dictionary 
			
		else:
			print("No passing variants found for chromosome",this_chrom,"")
			
		
			
		


'''
Skip sites with <4 genotyped individuals
Skip sites with >2 alleles

Processing algorithm:
	k = order of overlap (number of SNP nodes encompassed)
	for each SNP i, explore right until finding minimum-k conflict
	Add interval to data structure, increment i and continue
	
Data structure:
	Interval tree:
	Interval tree, but intervals indexed by k
	Solving goes from k=1 -> kmax

Or nested containment list might be better:https://academic.oup.com/bioinformatics/article/23/11/1386/199545

Solving algorithm:
	For each layer from k=1 to kmax:
		for each interval in layer k
			query center point of interval to get interval depth
			if overlaps exist:
				query each SNP-node centerpoint between interval start and end
				place break at centerpoint which maximizes depth, or center of maximum depth region
				delete all intervals intersecting with breakpoint

'''


class SNPcall():
	def __init__(self, pos, samps):
		self.position = int(pos)
		self.calls = list(samps)
	
	def __lt__(self, other):
		return(self.position < other.position)

	def FGT(self, other, rule):
		#print("Four gamete test for",self.position,"and",other.position)
		gametes = [0,0,0,0] #00, 01, 10, 11
		hets = list()
		
		genotypes = [[gt, other.calls[i]] for i, gt in enumerate(self.calls) if None not in [gt, other.calls[i]]]
		#print(genotypes)
		if (all(g in [0,1,2] for g in genotypes)): #make sure gt_types are valid
			print("Illegal genotype:",genotypes)
			return(None)
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
	
	@staticmethod
	def hapCheck(geno):
		if geno[0] == geno[1] == 0:
			return(0)
		elif geno[0] == geno[1] == 2:
			return(3)
		elif geno[0] == 0 and geno[1] == 2:
			return(1)
		elif geno[0] == 2 and geno[1] == 0:
			return(2)
		else:
			return None
	
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
		

#Function to write list of regions tuples, in GATK format
def write_regions(f, r):

	with open(f, 'w') as fh:
		try:
			for reg in r:
				ol = str(reg[0]) + ":" + str(reg[1]) + "-" + str(reg[2]) + "\n"
				fh.write(ol)
		except IOError as e:
			print("Could not read file %s: %s"%(f,e))
			sys.exit(1)
		except Exception as e:
			print("Unexpected error reading file %s: %s"%(f,e))
			sys.exit(1)
		finally:
			fh.close()



#Object to parse command-line arguments
class parseArgs():
	def __init__(self):
		#Define options
		try:
			options, remainder = getopt.getopt(sys.argv[1:], 'v:r:c:h', \
			[])
		except getopt.GetoptError as err:
			print(err)
			self.display_help("\nExiting because getopt returned non-zero exit status.")
		#Default values for params
		#Input params
		self.vcf=None
		self.rule=1
		self.chrom=None

		#First pass to see if help menu was called
		for o, a in options:
			if o in ("-h"):
				self.display_help("Exiting because help menu was called.")

		#Second pass to set all args.
		for opt, arg_raw in options:
			arg = arg_raw.replace(" ","")
			arg = arg.strip()
			opt = opt.replace("-","")
			#print(opt,arg)
			if opt == 'v':
				self.vcf = arg
			elif opt == 'r':
				self.rule=int(arg)
			elif opt == 'c':
				self.chrom = arg
			elif opt in ('h'):
				pass
			else:
				assert False, "Unhandled option %r"%opt

		#Check manditory options are set
		if not self.vcf:
			self.display_help("Must provide VCF file <-v,--vcf>")

		if self.rule not in [1, 2, 3]:
			self.display_help("Value for <-r> must be one of: 1, 2 or 3")

	def display_help(self, message=None):
		if message is not None:
			print()
			print (message)
		print ("\nFGTpartitioner.py\n")
		print ("Contact:Tyler K. Chafin, tylerkchafin@gmail.com")
		print ("\nUsage: ", sys.argv[0], "-v <input.vcf> -r <1|2|3> [-c chr1]\n")
		print ("Description: Computes minimal breakpoints to partition chromosomes into recombination-free blocks")

		print("""
	Arguments:
		-v	: VCF file for parsing
		-r	: Strategy to treat heterozygotes. Options:
			   1: Randomly haploidize heterozygous sites
			   2: Fail FGT if heterozygote might be incompatible
			   3: Pass FGT if heterozygote might be compatible
		-c	: Chromosome or contig in VCF to partition
		-h	: Displays help menu

""")
		print()
		sys.exit()

###overriding __lt__ method for Interval
def IntervalSort(self,other):
	return(self.data < other.data)

#Call main function
if __name__ == '__main__':
	Interval.__lt__ = IntervalSort
	main()
