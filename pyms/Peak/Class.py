"""
Provides a class to model signal peak
"""

################################################################################
#                                                                              #
#    PyMassSpec software for processing of mass-spectrometry data              #
#    Copyright (C) 2005-2012 Vladimir Likic                                    #
#    Copyright (C) 2019-2020 Dominic Davis-Foster                              #
#                                                                              #
#    This program is free software; you can redistribute it and/or modify      #
#    it under the terms of the GNU General Public License version 2 as         #
#    published by the Free Software Foundation.                                #
#                                                                              #
#    This program is distributed in the hope that it will be useful,           #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of            #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the             #
#    GNU General Public License for more details.                              #
#                                                                              #
#    You should have received a copy of the GNU General Public License         #
#    along with this program; if not, write to the Free Software               #
#    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.                 #
#                                                                              #
################################################################################

# stdlib
import copy
from typing import Any, Dict, List, Optional, Tuple, Union, cast
from warnings import warn

# 3rd party
import deprecation  # type: ignore

# this package
from pyms import __version__
from pyms.Base import pymsBaseClass
from pyms.IntensityMatrix import IntensityMatrix
from pyms.Spectrum import MassSpectrum
from pyms.Utils.Utils import is_sequence

__all__ = ["Peak"]


class Peak(pymsBaseClass):
	"""
	Models a signal peak.

	:param rt: Retention time
	:param ms: Either an ion mass, a mass spectrum or None
	:param minutes: Retention time units flag. If :py:obj:`True`, retention time
		is in minutes; if :py:obj:`False` retention time is in seconds.
	:param outlier: Whether the peak is an outlier

	:authors: Vladimir Likic, Andrew Isaac,
		Dominic Davis-Foster (type assertions and properties), David Kainer (outlier flag)
	"""

	_mass_spectrum: Optional[MassSpectrum]
	_ic_mass: Optional[float]

	def __init__(
			self,
			rt: Union[int, float] = 0.0,
			ms: Union[int, float, MassSpectrum, None] = None,
			minutes: bool = False,
			outlier: bool = False,
			):
		"""
		Models a signal peak
		"""

		if not isinstance(rt, (int, float)):
			raise TypeError("'rt' must be a number")

		if ms and not isinstance(ms, MassSpectrum) and not isinstance(ms, (int, float)):
			raise TypeError("'ms' must be a number or a MassSpectrum object")

		if minutes:
			rt = rt * 60.0

		# basic peak attributes
		self.is_outlier = outlier
		self._rt = float(rt)
		self._pt_bounds: Optional[Tuple[int, int, int]] = None
		self._area: Optional[float] = None
		self._ion_areas: Dict[float, float] = {}

		# these two attributes are required for
		# setting the peak mass spectrum
		if isinstance(ms, MassSpectrum):
			# mass spectrum
			self._mass_spectrum = ms
			self._ic_mass = None
		else:
			# single ion chromatogram properties
			self._mass_spectrum = None
			self._ic_mass = ms

		self.make_UID()

	def __eq__(self, other: Any) -> bool:
		"""
		Return whether this Peak object is equal to another object

		:param other: The other object to test equality with
		"""

		if isinstance(other, self.__class__):
			return (
					self.UID == other.UID and self.bounds == other.bounds and self.rt == other.rt
					and self.mass_spectrum == other.mass_spectrum and self.area == other.area
					and self.ic_mass == other.ic_mass
					)

		return NotImplemented

	# def __copy__(self):
	# 	#return pickle.loads(pickle.dumps(self))
	#
	# 	if self._mass_spectrum is None:
	# 		peak = Peak(rt=copy.copy(self._rt),
	# 					ms=copy.copy(self._ic_mass),
	# 					minutes=self._minutes,
	# 					outlier=self.is_outlier)
	# 	else:
	# 		peak = Peak(rt=copy.copy(self._rt),
	# 					ms=copy.copy(self._mass_spectrum),
	# 					minutes=self._minutes,
	# 					outlier=self.is_outlier)
	# 	if self._area is not None:
	# 		peak.area = self.area
	# 	if self._pt_bounds is not None:
	# 		peak.bounds = copy.copy(self.bounds)
	# 	if self._ic_mass is not None:
	# 		peak.ic_mass = 0+self.ic_mass
	#
	# 	return peak
	#
	# def __deepcopy__(self, memodict={}):
	# 	return self.__copy__()

	@property
	def area(self) -> Optional[float]:
		"""
		The area under the peak.

		:author: Andrew Isaac
		"""

		return self._area

	@area.setter
	def area(self, value: float):
		"""
		Sets the area under the peak.

		:param value: The peak area

		:author: Andrew Isaac
		"""

		if not isinstance(value, (int, float)):
			raise TypeError("'Peak.area' must be a positive number")
		elif value <= 0:
			raise ValueError("'Peak.area' must be a positive number")

		self._area = value

	@property
	def bounds(self) -> Optional[Tuple[int, int, int]]:
		"""
		The peak boundaries in points.

		:return: A 3-element tuple containing the left, apex, and right
			peak boundaries in points. Left and right are offsets.

		:author: Andrew Isaac
		"""

		return self._pt_bounds

	@bounds.setter
	def bounds(self, value: Tuple[int, int, int]):
		"""
		Sets peak boundaries in points

		:param value: A 3-element tuple containing the left, apex, and right
			peak boundaries in points. Left and right are offsets.
		"""

		if not is_sequence(value):
			raise TypeError("'Peak.bounds' must be a Sequence")

		if len(value) != 3:
			raise ValueError("'Peak.bounds' must have exactly 3 elements")

		for index, item in enumerate(value):
			if not isinstance(item, int):
				raise TypeError(f"'Peak.bounds' element #{index} must be an integer")

		self._pt_bounds = cast(Tuple[int, int, int], tuple(value[:3]))

	def crop_mass(self, mass_min: float, mass_max: float):
		"""
		Crops mass spectrum

		:param mass_min: Minimum mass value
		:param mass_max: Maximum mass value

		:author: Andrew Isaac
		"""

		if self._mass_spectrum is None:
			raise ValueError("Cannot crop the mass range of a single ion peak.")

		if not isinstance(mass_min, (int, float)) or not isinstance(mass_max, (int, float)):
			raise TypeError("'mass_min' and 'mass_max' must be numbers")

		if mass_min >= mass_max:
			raise ValueError("'mass_min' must be less than 'mass_max'")

		mass_list = self._mass_spectrum.mass_list

		if mass_min < min(mass_list):
			raise ValueError(f"'mass_min' is less than the smallest mass: {min(mass_list)}")

		if mass_max > max(mass_list):
			raise ValueError(f"'mass_max' is greater than the largest mass: {max(mass_list)}")

		# pre build mass_list and list of indices
		new_mass_list = []
		new_mass_spec = []
		mass_spec = self._mass_spectrum.mass_spec
		for ii in range(len(mass_list)):
			mass = mass_list[ii]
			if mass_min <= mass <= mass_max:
				new_mass_list.append(mass)
				new_mass_spec.append(mass_spec[ii])

		self._mass_spectrum.mass_list = new_mass_list
		self._mass_spectrum.mass_spec = new_mass_spec

		if len(new_mass_list) == 0:
			raise ValueError("mass spectrum is now empty")
		elif len(new_mass_list) < 10:
			warn("peak mass spectrum contains < 10 points", Warning)

		# update UID
		self.make_UID()

	def get_int_of_ion(self, ion: int) -> float:
		"""
		Returns the intensity of a given ion

		:param ion: The m/z value of the ion of interest

		:return: The intensity of the given ion in this peak
		"""

		if self._mass_spectrum is None:
			raise ValueError("Cannot use 'get_int_of_ion' with a single ion peak.")

		try:
			index = self._mass_spectrum.mass_list.index(ion)
			return self._mass_spectrum.mass_spec[index]
		except (ValueError, IndexError):
			raise IndexError(
					f"'ion' out of range of mass spectrum (range "
					f"{min(self._mass_spectrum.mass_list)} to "
					f"{max(self._mass_spectrum.mass_list)})"
					)

	def get_ion_area(self, ion: float) -> Optional[float]:
		"""
		Returns the area of a single ion chromatogram under the peak

		:param ion: The ion to calculate the area for
		:type ion: int

		:return: The area of the ion under this peak
		:rtype: float
		"""

		try:
			return self._ion_areas[ion]
		except KeyError:
			return None

	@deprecation.deprecated(
			deprecated_in="2.1.2",
			removed_in="2.2.0",
			current_version=__version__,
			details="Use :attr:`pyms.Peak.Class.Peak.ion_areas` instead",
			)
	def get_ion_areas(self) -> Dict:
		"""
		Returns a copy of the ion areas dict containing ion:ion area pairs
		"""

		return self.ion_areas

	def get_third_highest_mz(self) -> Optional[int]:
		"""
		Returns the *m/z* value with the third highest intensity.
		"""

		if self._mass_spectrum is not None:
			mass_list = self._mass_spectrum.mass_list
			mass_spec = self._mass_spectrum.mass_spec
			# find top two masses
			best = 0
			best_ii = 0
			best2_ii = 0
			best3_ii = 0
			for ii, intensity in enumerate(mass_spec):
				if intensity > best:
					best = intensity
					best3_ii = best2_ii
					best2_ii = best_ii
					best_ii = ii

			return int(mass_list[best3_ii])

		return None

	@property
	def ic_mass(self) -> Optional[float]:
		"""
		The mass for a single ion chromatogram peak.

		:return: The mass of the single ion chromatogram that the peak is from
		"""

		return self._ic_mass

	@ic_mass.setter
	def ic_mass(self, value: float):
		"""
		Sets the mass for a single ion chromatogram peak and clears the mass spectrum.

		:param value: The mass of the ion chromatogram that the peak is from
		"""

		if not isinstance(value, (int, float)):
			raise TypeError("'Peak.ic_mass' must be a number")

		self._ic_mass = value
		# clear mass spectrum
		self._mass_spectrum = None
		self.make_UID()

	@property
	def ion_areas(self) -> Dict:
		"""
		Returns a copy of the ion areas dict

		:return: The dictionary of ``ion: ion area`` pairs

		"""
		if len(self._ion_areas) == 0:
			raise ValueError("no ion areas set")

		return copy.deepcopy(self._ion_areas)

	@ion_areas.setter
	def ion_areas(self, value: Dict):
		"""
		Sets the ``ion: ion area`` pairs dictionary

		:param value: The dictionary of ion:ion_area pairs
		"""

		if not isinstance(value, dict) or not isinstance(list(value.keys())[0], (int, float)):
			raise TypeError("'Peak.ion_areas' must be a dictionary of ion:ion_area pairs")

		self._ion_areas = value

	def make_UID(self) -> None:
		"""
		Create a unique peak ID (UID), either:

		- Integer masses of top two intensities and their ratio (as ``Mass1-Mass2-Ratio*100``); or
		- the single mass as an integer and the retention time.

		:author: Andrew Isaac
		"""

		if self._mass_spectrum is not None:
			mass_list = self._mass_spectrum.mass_list
			mass_spec = self._mass_spectrum.mass_spec
			# find top two masses
			best = 0
			best_ii = 0
			best2_ii = 0
			for ii in range(len(mass_spec)):
				if mass_spec[ii] > best:
					best = mass_spec[ii]
					best2_ii = best_ii
					best_ii = ii
			ratio = int(100 * mass_spec[best2_ii] / best)
			self._UID = f"{int(mass_list[best_ii]):d}-{int(mass_list[best2_ii]):d}-{ratio:d}-{self._rt:.2f}"
		elif self._ic_mass is not None:
			self._UID = f"{int(self._ic_mass):d}-{self._rt:.2f}"
		else:
			self._UID = f"{self._rt:.2f}"

	@property
	def mass_spectrum(self) -> Optional[MassSpectrum]:
		"""
		The mass spectrum at the apex of the peak.
		"""

		return copy.copy(self._mass_spectrum)

	@mass_spectrum.setter
	def mass_spectrum(self, value: MassSpectrum):
		"""
		Sets the mass spectrum for the apex of the peak.

		Clears the mass for a single ion chromatogram peak.
		"""

		if not isinstance(value, MassSpectrum):
			raise TypeError("'Peak.mass_spectrum' must be a MassSpectrum object")

		self._mass_spectrum = value
		# clear ion mass
		self._ic_mass = None
		self.make_UID()

	def null_mass(self, mass: float):
		"""
		Ignore given mass in spectra

		:param mass: Mass value to remove

		:author: Andrew Isaac
		"""

		if self._mass_spectrum is None:
			raise NameError("mass spectrum not set for this peak")

		if not isinstance(mass, (int, float)):
			raise TypeError("'mass' must be a number")

		mass_list = self._mass_spectrum.mass_list

		if mass < min(mass_list) or mass > max(mass_list):
			raise IndexError("'mass' not in mass range:", min(mass_list), "to", max(mass_list))

		best = max(mass_list)
		ix = 0
		for ii in range(len(mass_list)):
			tmp = abs(mass_list[ii] - mass)
			if tmp < best:
				best = tmp
				ix = ii

		self._mass_spectrum.mass_spec[ix] = 0

		# update UID
		self.make_UID()

	@property
	def rt(self) -> float:
		"""
		The retention time of the peak.
		"""

		return self._rt

	def set_bounds(self, left: int, apex: int, right: int):
		"""
		Sets peak boundaries in points.

		:param left: Left peak boundary, in points offset from apex
		:param apex: Apex of the peak, in points
		:param right: Right peak boundary, in points offset from apex
		"""

		self.bounds = (left, apex, right)

	def set_ion_area(self, ion: int, area: float):
		"""
		sets the area for a single ion

		:param ion: the ion whose area is being entered
		:param area: the area under the IC of ion

		:author: Sean O'Callaghan
		"""

		if not isinstance(ion, int):
			raise TypeError("'ion' must be an integer")

		if not isinstance(area, (int, float)):
			raise TypeError("'area' must be a number")

		self._ion_areas[ion] = area

	@property
	def UID(self):
		"""
		Return the unique peak ID (UID), either:

		- Integer masses of top two intensities and their ratio (as ``Mass1-Mass2-Ratio*100``); or
		- the single mass as an integer and the retention time.

		:return: UID string

		:author: Andrew Isaac
		"""

		return self._UID

	def find_mass_spectrum(self, data: IntensityMatrix, from_bounds: float = False):
		"""
		TODO: What does this function do?

		Sets the peak's mass spectrum from the data.
		Clears the single ion chromatogram mass.

		:param data: An IntensityMatrix object
		:param from_bounds: Indicator whether to use the attribute 'pt_bounds'
			or to find the peak apex from the peak retention time
		"""

		if not isinstance(data, IntensityMatrix):
			raise TypeError("'data' must be an IntensityMatrix")

		if from_bounds:
			if self._pt_bounds is None:
				raise NameError("pt_bounds not set for this peak")
			else:
				pt_apex = self._pt_bounds[1]
		else:
			# get the index of peak apex from peak retention time
			pt_apex = data.get_index_at_time(self._rt)

		# set the mass spectrum
		self._mass_spectrum = data.get_ms_at_index(pt_apex)

		# clear single ion chromatogram mass
		self._ic_mass = None
		self.make_UID()

	def top_ions(self, num_ions: int = 5) -> List[float]:
		"""
		Computes the highest #num_ions intensity ions

		:param num_ions: The number of ions to be recorded

		:return: A list of the ions with the highest intensity.

		:authors: Sean O'Callaghan, Dominic Davis-Foster (type assertions)
		"""

		if not isinstance(num_ions, int):
			raise TypeError("'n_top_ions' must be an integer")

		if self.mass_spectrum is None:
			raise ValueError("Cannot retrieve the top_ions of a single ion peak.")

		intensity_list = self.mass_spectrum.mass_spec
		mass_list = self.mass_spectrum.mass_list

		ic_tuple = zip(intensity_list, mass_list)

		sorted_ic = sorted(ic_tuple)
		top_ic = sorted_ic[-num_ions:]

		top_ions = []

		for entry in top_ic:
			top_ions.append(entry[1])

		return top_ions

	#
	# def __dict__(self):
	#
	# 	return {
	# 			"UID": self.UID,
	# 			"bounds": self.bounds,
	# 			"area": self.area,
	# 			"is_outlier": self.is_outlier,
	# 			"ion_areas": self.ion_areas,
	# 			"mass_spectrum": self.mass_spectrum,
	# 			"rt": self.rt,
	# 			"ic_mass": self.ic_mass,
	#
	#
	#
	# 			}
	#
	# def __iter__(self):
	# 	for key, value in self.__dict__().items():
	# 		yield key, value
