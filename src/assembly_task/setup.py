from setuptools import find_packages, setup

package_name = 'assembly_task'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config',
            ['config/mvp1_pick_and_place.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ace',
    maintainer_email='3526623168@qq.com',
    description='TODO: Package description',
    license='Apache-2.0',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'assembly_task_node = assembly_task.assembly_task_node:main',
        ],
    },
)
