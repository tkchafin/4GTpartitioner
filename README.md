# FGTpartitioner
Partitions genome data using the 4-gamete test into a minimal number of blocks which contain no recombinations (=FGT conflicts)

Input is a VCF file, which can represent unphased genotypes, and output is a parsimonious set of breakpoints separating non-overlapping intervals which do not show evidence of recombination, as tested using the four-gamete test. 

Of note, there are multiple options for partioning a genome using the four-gamete test. Here are a few, sorry if I left anyone out:
-https://github.com/RILAB/rmin_cut
-https://github.com/YichaoOU/genome_partition
-http://www.csbio.unc.edu/mcmillan/pubs/BCB10_Wang.pdf

FGTpartitioner is my (admittedly inneficient) implementation, which is in part reinventing the wheel as a learning exercise. But, if you find it useful for your research, please just cite this GitHub page:
```
Chafin, TK. 2019. FGDpartitioner: https://github.com/tkchafin/FGTpartitioner
```


### Status
FGTpartitioner is currently working properly, and finds the same FGT conflicts as other programs that I have tested. However, it is currently very slow! I've sped it up slightly by Cython-izing a major bottleneck, and enabling a parallel search for FGT conflicts using the multiprocess module. I may spend a little more time profiling and optimizing, but the code does what I need it to do so I'll likely stop tinkering with it :)

### Dependencies
Requires Python 3 and the following modules:
- pyVCF 
- pySAM
- intervaltree
- Cython > 0.27 
- multiprocess

You will additionally need tabix installed to block-compress and index your VCF file (which enables me to parse it more quickly).

The easiest way to install all of the dependencies is through conda:
```
conda install -c conda-forge -c bioconda pyvcf intervaltree cython multiprocess pysam tabix
```

If you don't have conda installed, go [here](https://conda.io/en/latest/miniconda.html) and choose the correct Python3 installer for your system.

### Installation

To prep FGTpartioner for running, you will first need to pre-compile the cythonized portions of the code:
```
python setup.py build_ext --inplace
```
After that, FGTpartitioner is ready to run. You can view the help menu by typing:
```
./FGTpartitioner.py -h
```

### Inputs

The input file (provided via -v) is a standard VCF file, including contig lengths in the ##contig headers. You can find an example of a VCF file in the examples/ directory. In short, a minimally conforming VCF should have the following structure:
```
##fileformat=VCFv4.2
##contig=<ID=chr1.scaffold1,length=10000>
##FORMAT=<ID=GT,Number=1,Type=Integer,Description="Genotype">
##FORMAT=<ID=GP,Number=G,Type=Float,Description="Genotype Probabilities">
##FORMAT=<ID=PL,Number=G,Type=Float,Description="Phred-scaled Genotype Likelihoods">
#CHROM  POS     ID      REF     ALT     QUAL    FILTER  INFO    FORMAT  SAMP001 SAMP002 SAMP003 SAMP004
chr1.scaffold1  100     rs11449 G       A       .       PASS    .       GT      0/0     0/0     1/1     1/1
chr1.scaffold1  200     rs11449 T       A       .       PASS    .       GT      0/0     1/1     0/0     1/1
chr1.scaffold1  300 rs84825 A   T       .       PASS    .       GT      0/0     1/1     1/1     1/1
chr1.scaffold1  400 rs84825 A   G       .       PASS    .       GT      1/1
...
...
...
```

You will also need to block-compress and index your VCF file to speed up parsing:
```
#Run bgzip (NOT gzip) to compress your joint VCF file
bgzip file.vcf

#tabix to index it
tabix -h -f -p vcf file.vcf.gz
```
The result will be a binary compressed-VCF ".vcf.gz" file, and a ".vcf.gz.tbi" index file. The ".vcf.gz" will be the input provided to FGTpartitioner using the -v flag, and the '.vcf.gz.tbi" file should be in the same directory, and with the same prefix.

### Usage
You can view all of the possible options by calling the help menu in the command-line interface:

```
tyler:FGTpartitioner $ ./FGTpartitioner.py -h

Must provide VCF file <-v,--vcf>

FGTpartitioner.py

Contact:Tyler K. Chafin, tylerkchafin@gmail.com

Usage:  FGTpartitioner.py -v <input.vcf> -r <1|2|3> [-c chr1]

Description: Computes parsimonious breakpoints to partition chromosomes into recombination-free blocks

	Arguments:
		-v	: VCF file for parsing
		-r	: Strategy to treat heterozygotes. Options:
			   1: Randomly haploidize heterozygous sites
			   2: Fail FGT if heterozygote might be incompatible
			   3: Pass FGT if heterozygote might be compatible
		-c	: Chromosome or contig in VCF to partition
		-o	: Output file name [default: regions.out]
		-t	: Number of threads for parallel execution
		-m	: Minimum number of individuals genotyped to keep variant [default=2]
		-a	: Maximum number of alleles allowed per locus [default=2]
		-h	: Displays help menu
```
One important option which you will need to consider is <-r>, which determines how FGDpartioner behaves when it encounters heteroozygotes. The four-gamete test has several assumptions, the most important being: 1) That you have sampled haploid chromosomes; and 2) an [infinite-sites](https://en.wikipedia.org/wiki/Infinite_sites_model) mutation model (e.g. all mutations occur at a new site- no back mutation, or multiple mutations per site). You can find more details below in the "Four-Gamete Test" section.

In order to meet assumption #1, we need to manipulate our [unphased genotype data](https://www.biostars.org/p/7846/). FGDpartioner allows 3 ways in which this can be accomplished: #1: <-r 1>, Randomly choose one allele and treat the sample as homozygous for that allele, at that position; #2 : <-r 2> Ask if **either** allele causes a failure of the four-gamete test, and treat the comparison as failed if so (e.g. a pessimistic/safe approach); or #3 <-r 3> ask if **either** allele could possibly be consistent with the four-gametes assumption, and pass the comparison if so (e.g. an optimistic approach). This pessimistic/optimistic approach was inspired by [Wang et al (2010) Genome-wide compatible SNP intervals and their properties](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5690570/)

### The Four-Gamete Test

### Algorithm












### License
Copyright © 2019 Tyler K. Chafin <tylerkchafin@gmail.com>

This work is free. You can redistribute it and/or modify it under the
terms of the Do What The Fuck You Want To Public License, Version 2,
as published by Sam Hocevar. See http://www.wtfpl.net/ for more details.
