#!/usr/bin/env python3
"""Update only an API image in exported Helm JSON values, preserving all other values."""
import argparse
import json
import os
import re
import tempfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--values',type=Path,required=True)
    parser.add_argument('--repository',required=True)
    parser.add_argument('--tag',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(?:\.cn)?/[a-z0-9][a-z0-9._/-]*',args.repository):
        parser.error('Use the full existing private ECR repository URI without a tag')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}',args.tag) or args.tag=='latest':
        parser.error('Use a specific Docker image tag, not latest')
    raw=args.values.read_text()
    values=json.loads(raw)
    if not isinstance(values,dict) or not values:
        parser.error('Refusing empty Helm values; export the existing lab release first')
    if not isinstance(values.get('images'),dict):values['images']={}
    if not isinstance(values['images'].get('api'),dict):values['images']['api']={}
    values['images']['api'].update(repository=args.repository,tag=args.tag)
    backup=args.values.with_name(args.values.stem+'.backup.json')
    fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:stream.write(raw)
    fd,name=tempfile.mkstemp(dir=args.values.resolve().parent,prefix='.api-values-')
    try:
        with os.fdopen(fd,'w') as stream:json.dump(values,stream,indent=2);stream.write('\n')
        os.replace(name,args.values)
    finally:
        Path(name).unlink(missing_ok=True)
    print('Updated only API repository/tag; retained original values in a private backup.')

if __name__=='__main__':main()
