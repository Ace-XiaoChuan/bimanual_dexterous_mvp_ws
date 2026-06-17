from setuptools import find_packages, setup

package_name = 'fake_scene_manager'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ace',
    maintainer_email='3526623168@qq.com',
    description='Fake scene manager services for the MVP-0 assembly demo',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'fake_scene_manager_node = '
            'fake_scene_manager.fake_scene_manager_node:main',
        ],
    },
)
