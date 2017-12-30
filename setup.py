from setuptools import setup

setup(name='dxf2svg',
      version='0.1.0',
      description='Convert dxf to svg accountably.',
      author='Julian Todd',
      author_email='julian@goatchurch.org.uk',
      url='https://github.com/goatchurchprime/dxf2svg',
      packages=['dxf2svg'],
      install_requires=["dxfgrabber", "NURBS-Python"]
     )
